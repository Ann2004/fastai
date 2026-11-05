from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, EmailStr

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

api_router = APIRouter(prefix="/frontend-api")


class UserMe(BaseModel):
    email: EmailStr
    isActive: Annotated[bool, "Активен ли аккаунт"]
    profileId: Annotated[str, "ID профиля"]
    registeredAt: Annotated[datetime, "Дата регистрации"]
    updatedAt: Annotated[datetime, "Дата обновления"]
    username: Annotated[str, "Имя пользователя"]

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


@api_router.get("/users/me", response_model=UserMe)
def get_current_user():
    return {
        "email": "example@example.com",
        "isActive": True,
        "profileId": "1",
        "registeredAt": "2025-06-15T18:29:56+00:00",
        "updatedAt": "2025-06-15T18:29:56+00:00",
        "username": "user123",
    }


app = FastAPI(
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.include_router(api_router)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
