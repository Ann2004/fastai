from typing import Annotated

from fastapi import APIRouter, Path as FastPath, Request
from fastapi.responses import StreamingResponse

from schemas import SITE_EXAMPLE, Site, SiteCreateIn, SiteGenerateIn, SiteList, UserMe
from site_generation import stream_generated_site

users_router = APIRouter(prefix="/frontend-api/users", tags=["Users"])
sites_router = APIRouter(prefix="/frontend-api/sites", tags=["Sites"])


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
    return StreamingResponse(
        stream_generated_site(
            payload.prompt,
            s3_client=request.app.state.s3_client,
            gotenberg_client=request.app.state.gotenberg_client,
        ),
        media_type="text/plain; charset=utf-8",
    )


@sites_router.get("/{site_id}", response_model=Site)
def get_site(site_id: Annotated[int, FastPath(gt=0, title="ID сайта")]):
    """Получить сайт"""
    return {**SITE_EXAMPLE, "id": site_id}
