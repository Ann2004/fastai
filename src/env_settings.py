from pathlib import Path

from pydantic import PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class DeepSeekSettings(BaseSettings):
    api_key: SecretStr
    base_url: SecretStr
    model: SecretStr
    max_connections: PositiveInt = 5


class UnsplashSettings(BaseSettings):
    client_id: SecretStr
    max_connections: PositiveInt = 5
    timeout: PositiveInt = 20


class S3Settings(BaseSettings):
    endpoint_url: str
    access_key: SecretStr
    secret_key: SecretStr
    bucket: str
    region: str = "us-east-1"
    connect_timeout: PositiveInt = 10
    read_timeout: PositiveInt = 30
    max_connections: PositiveInt = 10


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
    debug: bool = False


settings = AppSettings()
