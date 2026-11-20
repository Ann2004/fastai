import logging
import os
import tempfile
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated

import aioboto3
from aiobotocore.config import AioConfig
import anyio
import httpx
from fastapi import APIRouter, FastAPI, Path as FastPath
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from furl import furl
from html_page_generator import (
    AsyncDeepseekClient,
    AsyncPageGenerator,
    AsyncUnsplashClient,
)
from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt, StringConstraints
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from env_settings import settings

logger = logging.getLogger("app.generate")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
GENERATED_HTML = BASE_DIR / "index.html"

SITE_HTML_KEY = "index.html"
SITE_SCREENSHOT_KEY = "screenshot.png"


def _object_url(key: str) -> str:
    return f"{settings.s3.endpoint_url.rstrip('/')}/{settings.s3.bucket}/{key}"


def _download_object_url(key: str) -> str:
    url = furl(_object_url(key))
    url.args["response-content-disposition"] = "attachment"
    return url.url


HTML_CODE_URL = _object_url(SITE_HTML_KEY)
HTML_CODE_DOWNLOAD_URL = _download_object_url(SITE_HTML_KEY)
SCREENSHOT_URL = _object_url(SITE_SCREENSHOT_KEY)

users_router = APIRouter(prefix="/frontend-api/users", tags=["Users"])
sites_router = APIRouter(prefix="/frontend-api/sites", tags=["Sites"])

SiteTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


class NormalizePathMiddleware(BaseHTTPMiddleware):
    """Схлопывает повторные слэши в пути запроса до роутинга."""
    async def dispatch(self, request: Request, call_next):
        if "//" in request.url.path:
            fixed = request.url.path
            while "//" in fixed:
                fixed = fixed.replace("//", "/")
            return RedirectResponse(url=str(request.url.replace(path=fixed)), status_code=307)
        return await call_next(request)


class UserMe(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    isActive: bool = Field(description="Активен ли аккаунт")
    profileId: str = Field(description="ID профиля")
    registeredAt: datetime = Field(description="Дата регистрации")
    updatedAt: datetime = Field(description="Дата обновления")
    username: str = Field(max_length=30, description="Имя пользователя")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "example@example.com",
                    "isActive": True,
                    "profileId": "1",
                    "registeredAt": "2025-06-15T18:29:56+00:00",
                    "updatedAt": "2025-06-15T18:29:56+00:00",
                    "username": "user123",
                },
            ],
        },
    )


SITE_EXAMPLE = {
    "createdAt": "2025-06-15T18:29:56+00:00",
    "htmlCodeDownloadUrl": HTML_CODE_DOWNLOAD_URL,
    "htmlCodeUrl": HTML_CODE_URL,
    "id": 1,
    "prompt": "Промпт генерации",
    "screenshotUrl": SCREENSHOT_URL,
    "title": "Компьютерный клуб",
    "updatedAt": "2025-06-15T18:29:56+00:00",
}


class Site(BaseModel):
    createdAt: datetime = Field(description="Дата создания")
    htmlCodeDownloadUrl: str = Field(description="URL для скачивания HTML")
    htmlCodeUrl: str = Field(description="URL HTML-кода")
    id: PositiveInt = Field(description="ID сайта")
    prompt: str = Field(description="Промпт генерации")
    screenshotUrl: str = Field(description="URL скриншота")
    title: SiteTitle = Field(description="Заголовок сайта")
    updatedAt: datetime = Field(description="Дата обновления")

    model_config = ConfigDict(json_schema_extra={"examples": [SITE_EXAMPLE]})


class SiteList(BaseModel):
    sites: list[Site]


class SiteCreateIn(BaseModel):
    prompt: str = Field(description="Промпт генерации")
    title: SiteTitle | None = Field(
        default=None,
        description="Заголовок сайта",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "prompt": "Сайт любителей играть в домино",
                    "title": "Фан клуб игры в домино",
                },
            ],
        },
    )


class SiteGenerateIn(BaseModel):
    prompt: str = Field(description="Промпт генерации")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"prompt": "Сайт любителей играть в домино"}],
        },
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация клиентов DeepSeek/Unsplash/S3...")

    unsplash_client = AsyncUnsplashClient.setup(
        settings.unsplash.client_id.get_secret_value(),
        timeout=settings.unsplash.timeout,
    )
    deepseek_client = AsyncDeepseekClient.setup(
        settings.deepseek.api_key.get_secret_value(),
        settings.deepseek.base_url.get_secret_value(),
        settings.deepseek.model.get_secret_value(),
    )

    await unsplash_client.__aenter__()
    await deepseek_client.__aenter__()

    app.state.deepseek_cm = deepseek_client
    app.state.unsplash_cm = unsplash_client

    app.state.s3_session = aioboto3.Session()
    app.state.s3_config = AioConfig(
        connect_timeout=settings.s3.connect_timeout,
        read_timeout=settings.s3.read_timeout,
        max_pool_connections=settings.s3.max_connections,
    )

    try:
        yield
    finally:
        logger.info("Закрытие клиентов DeepSeek/Unsplash...")
        try:
            await deepseek_client.__aexit__(None, None, None)
        except Exception:
            logger.exception("Ошибка при закрытии DeepSeek клиента")
        try:
            await unsplash_client.__aexit__(None, None, None)
        except Exception:
            logger.exception("Ошибка при закрытии Unsplash клиента")


def _s3_client(s3_session: aioboto3.Session, s3_config: AioConfig):
    return s3_session.client(
        "s3",
        endpoint_url=settings.s3.endpoint_url,
        aws_access_key_id=settings.s3.access_key.get_secret_value(),
        aws_secret_access_key=settings.s3.secret_key.get_secret_value(),
        region_name=settings.s3.region,
        config=s3_config,
    )


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=".index-", suffix=".html", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


@users_router.get("/me", response_model=UserMe)
def get_current_user():
    """Получить учетные данные пользователя"""
    return {
        "email": "example@example.com",
        "isActive": True,
        "profileId": "1",
        "registeredAt": "2025-06-15T18:29:56+00:00",
        "updatedAt": "2025-06-15T18:29:56+00:00",
        "username": "user123",
    }


@sites_router.get("/my", response_model=SiteList)
def get_my_sites():
    """Получить список сгенерированных сайтов текущего пользователя"""
    return {"sites": [SITE_EXAMPLE]}


@sites_router.post("/create", response_model=Site)
def create_site(payload: SiteCreateIn):
    """Создать сайт"""
    return {
        **SITE_EXAMPLE,
        "title": payload.title or SITE_EXAMPLE["title"],
        "prompt": payload.prompt,
    }


HTML_START_MARKERS = ("<!DOCTYPE", "<html")
HTML_END_MARKER = "</html>"


async def _stream_generated_site(
    user_prompt: str,
    *,
    s3_session: aioboto3.Session,
    s3_config: AioConfig,
) -> AsyncGenerator[str, None]:
    generator = AsyncPageGenerator(debug_mode=settings.debug)

    collected_chunks: list[str] = []
    title_printed = False

    pre_html_buffer = ""
    html_started = False
    html_finished = False

    try:
        async for chunk in generator(user_prompt):
            if not isinstance(chunk, str):
                continue

            collected_chunks.append(chunk)

            if not html_started:
                pre_html_buffer += chunk
                start_idx = -1
                for marker in HTML_START_MARKERS:
                    idx = pre_html_buffer.find(marker)
                    if idx != -1 and (start_idx == -1 or idx < start_idx):
                        start_idx = idx
                if start_idx == -1:
                    continue

                html_started = True
                tail = pre_html_buffer[start_idx:]
                pre_html_buffer = ""

                if not title_printed and generator.html_page.title:
                    logger.info("Заголовок страницы: %r", generator.html_page.title)
                    title_printed = True

                end_idx = tail.find(HTML_END_MARKER)
                if end_idx != -1:
                    yield tail[: end_idx + len(HTML_END_MARKER)]
                    html_finished = True
                    break

                yield tail
                continue

            if html_finished:
                continue

            end_idx = chunk.find(HTML_END_MARKER)
            if end_idx != -1:
                yield chunk[: end_idx + len(HTML_END_MARKER)]
                html_finished = True
                break

            yield chunk

    except anyio.get_cancelled_exc_class():
        logger.warning("Генерация отменена. Сохраняется best-effort результат.")
        raise

    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        logger.exception("Ошибка внешнего сервиса: %s", exc)
        if not html_started:
            yield "[ОШИБКА] Внешний сервис недоступен. Попробуйте позже."
        return

    except Exception:
        logger.exception("Непредвиденная ошибка генерации")
        if not html_started:
            yield "[ОШИБКА] Внутренняя ошибка генерации."
        return

    finally:
        html_to_save: str | None = None

        try:
            page = getattr(generator, "html_page", None)
            if page is not None and page.html_code:
                html_to_save = page.html_code
        except Exception:
            logger.exception("Не удалось прочитать generator.html_page.html_code")

        if not html_to_save and collected_chunks:
            html_to_save = "".join(collected_chunks)

        if html_to_save is not None:
            with anyio.CancelScope(shield=True):
                try:
                    _atomic_write_text(GENERATED_HTML, html_to_save)
                    logger.info("HTML сохранён в %s (%d байт)", GENERATED_HTML, len(html_to_save))
                except Exception:
                    logger.exception("Не удалось сохранить %s", GENERATED_HTML)

                try:
                    async with _s3_client(s3_session, s3_config) as s3:
                        await s3.put_object(
                            Bucket=settings.s3.bucket,
                            Key=SITE_HTML_KEY,
                            Body=html_to_save.encode("utf-8"),
                            ContentType="text/html; charset=utf-8",
                            ContentDisposition="inline",
                        )
                    logger.info(
                        "HTML загружен в S3: %s/%s (%d байт)",
                        settings.s3.bucket, SITE_HTML_KEY, len(html_to_save),
                    )
                except Exception:
                    logger.exception("Не удалось загрузить HTML в S3")
        else:
            logger.warning("Нечего сохранять: генератор не вернул HTML.")


@sites_router.post(
    "/{site_id}/generate",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"text/plain": {}},
            "description": "Поток HTML-кода",
        },
    },
)
async def generate_site(
    request: Request,
    site_id: Annotated[int, FastPath(gt=0, title="ID сайта")],
    payload: SiteGenerateIn,
):
    logger.info("Запрос генерации сайта id=%s, prompt=%r", site_id, payload.prompt)

    return StreamingResponse(
        _stream_generated_site(
            payload.prompt,
            s3_session=request.app.state.s3_session,
            s3_config=request.app.state.s3_config,
        ),
        media_type="text/plain; charset=utf-8",
    )


@sites_router.get("/{site_id}", response_model=Site)
def get_site(site_id: Annotated[int, FastPath(gt=0, title="ID сайта")]):
    """Получить сайт"""
    return {**SITE_EXAMPLE, "id": site_id}


app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(NormalizePathMiddleware)

app.include_router(users_router)
app.include_router(sites_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
