import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, FastAPI, Path as FastPath
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt, StringConstraints
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SITE_HTML = STATIC_DIR / "site.html"

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
    "htmlCodeDownloadUrl": "https://dvmn.org/media/filer_public/d1/4b/d14bb4e8-d8b4-49cb-928d-fd04ecae46da/index.html",
    "htmlCodeUrl": "https://dvmn.org/media/filer_public/d1/4b/d14bb4e8-d8b4-49cb-928d-fd04ecae46da/index.html",
    "id": 1,
    "prompt": "Сайт любителей играть в домино",
    "screenshotUrl": "https://s13.stc.yc.kpcdn.net/share/i/12/13875743/wr-960.webp",
    "title": "Фан клуб Домино",
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


async def _stream_site_html() -> AsyncGenerator[str, None]:
    html = SITE_HTML.read_text(encoding="utf-8")
    chunk_size = 64
    for i in range(0, len(html), chunk_size):
        yield html[i : i + chunk_size]
        await asyncio.sleep(0.05)


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
async def generate_site(site_id: Annotated[int, FastPath(gt=0, title="ID сайта")], payload: SiteGenerateIn):
    """Сгенерировать HTML код сайта"""
    return StreamingResponse(
        _stream_site_html(),
        media_type="text/plain; charset=utf-8",
    )


@sites_router.get("/{site_id}", response_model=Site)
def get_site(site_id: Annotated[int, FastPath(gt=0, title="ID сайта")]):
    """Получить сайт"""
    return {**SITE_EXAMPLE, "id": site_id}


app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(NormalizePathMiddleware)

app.include_router(users_router)
app.include_router(sites_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
