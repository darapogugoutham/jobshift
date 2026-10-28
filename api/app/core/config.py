from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://jobshift:jobshift_dev@localhost:5432/jobshift"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    session_cookie_name: str = "jobshift_session"
    session_ttl_hours: int = Field(default=24, ge=1, le=24)
    secure_cookies: bool = False
    import_preview_ttl_minutes: int = 30
    max_upload_bytes: int = 5 * 1024 * 1024
    max_workbook_expanded_bytes: int = 25 * 1024 * 1024
    max_workbook_cells: int = 20_000

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
