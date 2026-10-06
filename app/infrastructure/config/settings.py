from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_env: str = "development"
    app_debug: bool = True
    app_name: str = "GameManager"
    app_version: str = "1.0.0"

    secret_key: str
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    database_url: str = "sqlite:///./sqlite.db"

    admin_email: str = "alfredo.villegas.hk@gmail.com"
    admin_username: str = "admin"
    admin_password: str = "admin123"

    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
