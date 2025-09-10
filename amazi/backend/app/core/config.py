import os
from functools import lru_cache


class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    database_url_async: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/amazi",
    )
    database_url_sync: str = os.getenv(
        "SYNC_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/amazi",
    )
    timezone: str = os.getenv("TIMEZONE", "US/Eastern")
    storage_dir: str = os.getenv("STORAGE_DIR", "/workspace/amazi/storage")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "5"))
    allowed_file_types: set[str] = set(
        os.getenv("ALLOWED_FILE_TYPES", "csv,xlsx,pdf,jpg,jpeg,png,heic").split(",")
    )
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.storage_dir, exist_ok=True)
    return settings

