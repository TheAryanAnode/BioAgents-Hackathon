from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    google_api_key: str = ""
    gemini_fast_model: str = "gemini-2.5-flash"
    gemini_deep_model: str = "gemini-2.5-pro"
    gemini_embed_model: str = "text-embedding-004"
    entrez_email: str = ""

    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"

    max_papers: int = 40
    max_pdf_pages: int = 30
    max_pdf_chars: int = 120_000

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.google_api_key.strip())

    def ensure_dirs(self) -> None:
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
