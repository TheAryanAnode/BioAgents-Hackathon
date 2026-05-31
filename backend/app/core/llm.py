"""Thin Gemini wrapper. Returns ``None`` when unavailable so callers fall back
to deterministic heuristics — the app must work without an API key."""

from __future__ import annotations

import json
import re
from typing import Optional

from app.core.config import get_settings


class LLM:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._fast = None
        self._deep = None
        if self.settings.gemini_enabled:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._fast = ChatGoogleGenerativeAI(
                    model=self.settings.gemini_fast_model,
                    google_api_key=self.settings.google_api_key,
                    temperature=0.3,
                )
                self._deep = ChatGoogleGenerativeAI(
                    model=self.settings.gemini_deep_model,
                    google_api_key=self.settings.google_api_key,
                    temperature=0.5,
                )
            except Exception:
                self._fast = self._deep = None

    @property
    def enabled(self) -> bool:
        return self._fast is not None

    def complete(self, prompt: str, deep: bool = False) -> Optional[str]:
        model = self._deep if deep else self._fast
        if model is None:
            return None
        try:
            return model.invoke(prompt).content  # type: ignore[union-attr]
        except Exception:
            return None

    def complete_json(self, prompt: str, deep: bool = False) -> Optional[dict | list]:
        text = self.complete(
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
    # Best-effort: grab the first balanced JSON object/array.
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
