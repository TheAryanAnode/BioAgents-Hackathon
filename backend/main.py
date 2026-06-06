"""Vercel FastAPI entrypoint — mounted at /_/backend via experimentalServices."""
from app.main import app

__all__ = ["app"]
