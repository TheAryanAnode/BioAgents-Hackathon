"""Thin Nebius Token Factory wrapper (OpenAI-compatible chat completions).

Returns ``None`` when unavailable so callers fall back to deterministic
heuristics — the app must work without an API key.

Nebius is used ONLY for user-initiated calls:
- chat messages
- clicking a hypothesis (one call per hypothesis, once)
- generating a full investment report
- investigation synthesizer narrative

The research pipeline (graph, evidence, hypotheses) always uses heuristics.
"""

from __future__ import annotations

import json
import re
import time
from typing import Optional

import httpx

from app.core.config import get_settings

_SYSTEM = (
    "You are SynthesisOS, a helpful biomedical and scientific research assistant. "
    "Answer any reasonable question the user asks. Session-specific literature is "
    "optional context — never refuse a question because it is outside the current "
    "research topic."
)


class LLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._cooldown_until = 0.0
        self._window_start = time.monotonic()
        self._calls_in_window = 0
        self.quota_exhausted = False
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return self.settings.llm_enabled

    @property
    def provider(self) -> str:
        return "nebius" if self.enabled else "demo"

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
        return self._calls_in_window < self.settings.llm_max_rpm

    @property
    def pipeline_llm_allowed(self) -> bool:
        return self.enabled and self.settings.llm_use_in_pipeline and self.can_call()

    def _register_call(self) -> None:
        self._calls_in_window += 1

    def _handle_error(self, exc: Exception) -> None:
        msg = str(exc)
        self.last_error = msg[:200]
        low = msg.lower()
        if "429" in msg or "rate" in low or "quota" in low or "too many" in low:
            self.quota_exhausted = True
            self._cooldown_until = time.monotonic() + self.settings.llm_quota_cooldown_seconds

    def _invoke(self, prompt: str, *, deep: bool = False) -> str:
        model = self.settings.nebius_deep_model if deep else self.settings.nebius_model
        url = f"{self.settings.nebius_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5 if deep else 0.3,
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            resp = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.settings.nebius_api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("Nebius returned no choices")
        content = choices[0].get("message", {}).get("content")
        if not content:
            raise RuntimeError("Nebius returned empty content")
        return str(content)

    def complete(self, prompt: str, deep: bool = False, *, force: bool = False) -> Optional[str]:
        """``force=True`` bypasses pipeline budget checks (chat / report). Still rate-limited."""
        if not self.enabled:
            return None
        if not force and not self.settings.llm_use_in_pipeline:
            return None
        if not self.can_call():
            return None
        try:
            self._register_call()
            return self._invoke(prompt, deep=deep)
        except Exception as exc:
            self._handle_error(exc)
            return None

    def complete_interactive(self, prompt: str, deep: bool = False) -> Optional[str]:
        """User-facing calls (chat, report) — always attempt when under RPM cap."""
        if not self.enabled or not self.can_call():
            return None
        try:
            self._register_call()
            return self._invoke(prompt, deep=deep)
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
