from functools import lru_cache
import os
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
    # Free tier ≈5 RPM — keep pipeline off Gemini by default; chat/report use the budget.
    gemini_use_in_pipeline: bool = False
    gemini_use_for_embeddings: bool = False
    gemini_max_rpm: int = 4
    gemini_timeout_seconds: float = 20.0
    gemini_quota_cooldown_seconds: float = 55.0
    entrez_email: str = ""

    # CRAFT / Emergence MCP — real-world evidence investigation (IDC + PanCancer).
    # Without a token the client runs in deterministic demo mode so the feature
    # always works offline (mirrors the Gemini-optional philosophy).
    emergence_project_id: str = "1ac58445-c4ad-49db-b392-17c8003729ef"
    emergence_mcp_url: str = "https://nebius.emergence.ai/mcp"
    emergence_mcp_token: str = ""
    craft_pancancer_connection: str = "pancancer-atlas-1-1ac58445"
    craft_idc_connection: str = "idc-1ac58445"
    craft_max_queries_per_investigation: int = 6
    craft_timeout_seconds: float = 30.0

    data_dir: str = "./data"
    upload_dir: str = "./data/uploads"

    max_papers: int = 40
    max_pdf_pages: int = 30
    max_pdf_chars: int = 120_000

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    allow_origin_regex: str = ""  # e.g. https://.*\.vercel\.app for production

    @property
    def is_vercel(self) -> bool:
        return bool(os.getenv("VERCEL"))

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def origin_regex(self) -> str | None:
        r = self.allow_origin_regex.strip()
        return r or None

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.google_api_key.strip())

    @property
    def craft_live(self) -> bool:
        """True when a real MCP token is configured; otherwise demo mode."""
        return bool(self.emergence_mcp_token.strip() and self.emergence_project_id.strip())

    def ensure_dirs(self) -> None:
        if self.is_vercel:
            self.data_dir = "/tmp/synthesisos/data"
            self.upload_dir = "/tmp/synthesisos/uploads"
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s
