"""Thin Gemini wrapper. Returns ``None`` when unavailable so callers fall back
to deterministic heuristics — the app must work without an API key.

Free-tier Gemini is ~5 requests/minute. The bulk pipeline therefore avoids
LLM calls by default; chat and on-demand report generation use the budget.
"""

from __future__ import annotations

import json
import re
import time
from typing import Optional

from app.core.config import get_settings


class LLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._fast = None
        self._deep = None
        self._cooldown_until = 0.0
        self._window_start = time.monotonic()
        self._calls_in_window = 0
        self.quota_exhausted = False
        self.last_error: str | None = None

        if self.settings.gemini_enabled:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                common = dict(
                    google_api_key=self.settings.google_api_key,
                    max_retries=0,  # never block the pipeline on 16s/32s langchain retries
                    timeout=self.settings.gemini_timeout_seconds,
                )
                self._fast = ChatGoogleGenerativeAI(
                    model=self.settings.gemini_fast_model,
                    temperature=0.3,
                    **common,
                )
                self._deep = ChatGoogleGenerativeAI(
                    model=self.settings.gemini_deep_model,
                    temperature=0.5,
                    **common,
                )
            except Exception:
                self._fast = self._deep = None

    @property
    def enabled(self) -> bool:
        return self._fast is not None

    def _reset_window(self) -> None:
        now = time.monotonic()
        if now - self._window_start >= 60:
            self._window_start = now
            self._calls_in_window = 0
            if self.quota_exhausted and now >= self._cooldown_until:
                self.quota_exhausted = False

    def can_call(self) -> bool:
        if not self.enabled:
            return False
        self._reset_window()
        if time.monotonic() < self._cooldown_until:
            return False
        return self._calls_in_window < self.settings.gemini_max_rpm

    @property
    def pipeline_llm_allowed(self) -> bool:
        return self.enabled and self.settings.gemini_use_in_pipeline and self.can_call()

    def _register_call(self) -> None:
        self._calls_in_window += 1

    def _handle_error(self, exc: Exception) -> None:
        msg = str(exc)
        self.last_error = msg[:200]
        if "429" in msg or "ResourceExhausted" in type(exc).__name__ or "quota" in msg.lower():
            self.quota_exhausted = True
            self._cooldown_until = time.monotonic() + self.settings.gemini_quota_cooldown_seconds

    def complete(self, prompt: str, deep: bool = False, *, force: bool = False) -> Optional[str]:
        """``force=True`` bypasses pipeline budget checks (chat / report). Still rate-limited."""
        if not self.enabled:
            return None
        if not force and not self.settings.gemini_use_in_pipeline:
            return None
        if not self.can_call():
            return None

        model = self._deep if deep else self._fast
        if model is None:
            return None
        try:
            self._register_call()
            return model.invoke(prompt).content  # type: ignore[union-attr]
        except Exception as exc:
            self._handle_error(exc)
            return None

    def complete_interactive(self, prompt: str, deep: bool = False) -> Optional[str]:
        """User-facing calls (chat, report) — always attempt when under RPM cap."""
        if not self.enabled or not self.can_call():
            return None
        model = self._deep if deep else self._fast
        if model is None:
            return None
        try:
            self._register_call()
            return model.invoke(prompt).content  # type: ignore[union-attr]
        except Exception as exc:
            self._handle_error(exc)
            return None

    def complete_json(self, prompt: str, deep: bool = False) -> Optional[dict | list]:
        text = self.complete(
            prompt + "\n\nRespond ONLY with valid minified JSON. No markdown fences.",
            deep=deep,
        )
        if not text:
            return None
        return _extract_json(text)

    def complete_json_interactive(self, prompt: str, deep: bool = False) -> Optional[dict | list]:
        text = self.complete_interactive(
            prompt + "\n\nRespond ONLY with valid minified JSON. No markdown fences.",
            deep=deep,
        )
        if not text:
            return None
        return _extract_json(text)


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        start = text.find(open_c)
        end = text.rfind(close_c)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                continue
    return None


_llm: Optional[LLM] = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm


def reset_llm() -> None:
    """Clear cached client (e.g. after .env change)."""
    global _llm
    _llm = None
