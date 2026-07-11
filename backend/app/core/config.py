from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    nebius_api_key: str = ""
    nebius_base_url: str = "https://api.tokenfactory.us-central1.nebius.com/v1"
    nebius_model: str = "MiniMaxAI/MiniMax-M3"
    nebius_deep_model: str = "MiniMaxAI/MiniMax-M3"
    # Keep pipeline off the LLM by default; chat / enrich / report use the budget.
    llm_use_in_pipeline: bool = False
    llm_max_rpm: int = 30
    llm_timeout_seconds: float = 60.0
    llm_quota_cooldown_seconds: float = 10.0
    entrez_email: str = ""

    # CRAFT / Emergence MCP — real-world evidence investigation (IDC + PanCancer).
    # Without a token the client runs in deterministic demo mode so the feature
    # always works offline (mirrors the LLM-optional philosophy).
    emergence_project_id: str = "1ac58445-c4ad-49db-b392-17c8003729ef"
    emergence_mcp_url: str = "https://nebius.emergence.ai/mcp"
    emergence_mcp_token: str = ""
    craft_pancancer_connection: str = "pancancer-atlas-1-1ac58445"
    craft_idc_connection: str = "idc-1ac58445"
    # Other Spider-2.0 connections used by the chat text-to-SQL router. These are
    # best-guess default slugs; when a live token is set, the exact slug is
    # resolved at runtime via list_data_connections (name/description match).
    craft_ecommerce_connection: str = "thelook-ecommerce-1ac58445"
    craft_ecommerce_br_connection: str = "brazilian-e-commerce-1ac58445"
    craft_crypto_connection: str = "crypto-1ac58445"
    craft_ga4_connection: str = "ga4-1ac58445"
    craft_firebase_connection: str = "firebase-1ac58445"
    craft_github_connection: str = "github-repos-1ac58445"
    craft_deps_connection: str = "deps-dev-v1-1ac58445"
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
    def llm_enabled(self) -> bool:
        return bool(self.nebius_api_key.strip())

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
