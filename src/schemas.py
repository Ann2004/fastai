from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    PositiveInt,
    StringConstraints,
)

from urls import HTML_CODE_DOWNLOAD_URL, HTML_CODE_URL, SCREENSHOT_URL

SiteTitle = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]


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
    "prompt": "Создай лендинг для пекарни. Сайт должен быть простым и легким, он должен мало весить. На сайте только одна фотография",
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
