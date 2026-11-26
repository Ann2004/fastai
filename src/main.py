import logging
from contextlib import asynccontextmanager
from pathlib import Path

import aioboto3
import httpx
from aiobotocore.config import AioConfig
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from html_page_generator import AsyncDeepseekClient, AsyncUnsplashClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from env_settings import settings
from routers import sites_router, users_router

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class NormalizePathMiddleware(BaseHTTPMiddleware):
    """Схлопывает повторные слэши в пути запроса до роутинга."""
    async def dispatch(self, request: Request, call_next):
        if "//" in request.url.path:
            fixed = request.url.path
            while "//" in fixed:
                fixed = fixed.replace("//", "/")
            return RedirectResponse(url=str(request.url.replace(path=fixed)), status_code=307)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация клиентов DeepSeek/Unsplash/S3...")

    unsplash_client = AsyncUnsplashClient.setup(
        settings.unsplash.client_id.get_secret_value(),
        timeout=settings.unsplash.timeout,
        limits=httpx.Limits(max_connections=settings.unsplash.max_connections),
    )
    deepseek_client = AsyncDeepseekClient.setup(
        settings.deepseek.api_key.get_secret_value(),
        settings.deepseek.base_url,
        settings.deepseek.model,
        limits=httpx.Limits(max_connections=settings.deepseek.max_connections),
    )

    await unsplash_client.__aenter__()
    await deepseek_client.__aenter__()

    app.state.deepseek_cm = deepseek_client
    app.state.unsplash_cm = unsplash_client

    s3_session = aioboto3.Session()
    s3_config = AioConfig(
        connect_timeout=settings.s3.connect_timeout,
        read_timeout=settings.s3.read_timeout,
        max_pool_connections=settings.s3.max_connections,
    )
    s3_cm = s3_session.client(
        "s3",
        endpoint_url=settings.s3.endpoint_url,
        aws_access_key_id=settings.s3.access_key.get_secret_value(),
        aws_secret_access_key=settings.s3.secret_key.get_secret_value(),
        region_name=settings.s3.region,
        config=s3_config,
    )
    app.state.s3_cm = s3_cm
    app.state.s3_client = await s3_cm.__aenter__()

    app.state.gotenberg_client = httpx.AsyncClient(
        base_url=str(settings.gotenberg.base_url),
        timeout=settings.gotenberg.timeout,
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
        try:
            await app.state.s3_cm.__aexit__(None, None, None)
        except Exception:
            logger.exception("Ошибка при закрытии S3-клиента")
        try:
            await app.state.gotenberg_client.aclose()
        except Exception:
            logger.exception("Ошибка при закрытии Gotenberg-клиента")


app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(NormalizePathMiddleware)

app.include_router(users_router)
app.include_router(sites_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
