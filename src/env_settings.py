from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, HttpUrl, PositiveInt, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]
StrHttpUrl = Annotated[HttpUrl, AfterValidator(str)]
ScreenshotFormat = Literal["png", "jpeg", "webp"]

SCREENSHOT_MIME: dict[ScreenshotFormat, str] = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

SCREENSHOT_EXT: dict[ScreenshotFormat, str] = {
    "png": "png",
    "jpeg": "jpg",
    "webp": "webp",
}


class DeepSeekSettings(BaseSettings):
    api_key: SecretStr
    base_url: StrHttpUrl
    model: NonEmptyStr
    max_connections: PositiveInt = 5


class UnsplashSettings(BaseSettings):
    client_id: SecretStr
    max_connections: PositiveInt = 5
    timeout: PositiveInt = 20


class S3Settings(BaseSettings):
    endpoint_url: StrHttpUrl
    access_key: SecretStr
    secret_key: SecretStr
    bucket: NonEmptyStr
    region: str = "us-east-1"
    connect_timeout: PositiveInt = 10
    read_timeout: PositiveInt = 30
    max_connections: PositiveInt = 10


class GotenbergSettings(BaseSettings):
    base_url: StrHttpUrl = "https://demo.gotenberg.dev"
    timeout: PositiveInt = 15
    screenshot_width: PositiveInt = 1000
    screenshot_format: ScreenshotFormat = "png"
    wait_delay: PositiveInt = 5


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        validate_default=None,
        env_nested_delimiter="__",
    )

    deepseek: DeepSeekSettings
    unsplash: UnsplashSettings
    s3: S3Settings
    gotenberg: GotenbergSettings
    debug: bool = False


settings = AppSettings()
