"""
Centralized Gemini LLM client, task defaults, and retry helpers for Project Aether.
"""

from __future__ import annotations

import logging
import threading
import time
import warnings
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger("ProjectAether.LLM")

DEFAULT_LLM_MODEL = "gemini-4-hydrogen"

SUPPORTED_MODELS = (
    "gemini-4-hydrogen",
    "gemini-4-neon",
    "gemini-4-argon",
    "gemini-4-carbon",
    "gemini-flash-latest",
)

THINKING_LEVELS = ("low", "medium", "high", "xhigh")

_CLIENT_LOCK = threading.Lock()
_CLIENTS: dict[str, genai.Client] = {}


class QuotaExhaustedError(Exception):
    """Raised when the Gemini API quota is exhausted after retries."""


def get_genai_client(api_key: str) -> genai.Client:
    """Return a cached thread-safe `genai.Client` for the given API key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    with _CLIENT_LOCK:
        client = _CLIENTS.get(key)
        if client is None:
            client = genai.Client(api_key=key)
            _CLIENTS[key] = client
        return client


def normalize_thinking_level(level: str | None, default: str = "low") -> str:
    """Normalize a thinking level string to a supported Gemini 4 level."""
    value = (level or default).strip().lower()
    if value in THINKING_LEVELS:
        return value
    if value == "minimal":
        return "low"
    return default


def build_thinking_config(thinking_level: str | None) -> types.ThinkingConfig:
    """Build a `types.ThinkingConfig` for `low`, `medium`, `high`, or `xhigh`."""
    level = normalize_thinking_level(thinking_level)
    mapping = {
        "low": types.ThinkingLevel.LOW,
        "medium": types.ThinkingLevel.MEDIUM,
        "high": types.ThinkingLevel.HIGH,
    }
    if level in mapping:
        return types.ThinkingConfig(thinking_level=mapping[level])

    # `xhigh` is supported by Gemini 4 Hydrogen/Neon even if older SDK enums warn.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*is not a valid ThinkingLevel.*")
        return types.ThinkingConfig(thinking_level=level)  # type: ignore[arg-type]


def _is_rate_limit_or_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "429",
            "503",
            "500",
            "resource_exhausted",
            "rate limit",
            "unavailable",
            "overloaded",
            "timeout",
            "timed out",
        )
    )


def _is_hard_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "resource_exhausted" in msg or "quota" in msg


def generate_content(
    *,
    api_key: str,
    model: str,
    contents: Any,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    thinking_level: str = "low",
    response_mime_type: str | None = None,
    response_schema: type[BaseModel] | None = None,
    max_retries: int = 3,
) -> Any:
    """
    Execute `client.models.generate_content` with transient backoff and
    structured-output support.
    """
    client = get_genai_client(api_key)

    config_kwargs: dict[str, Any] = {
        "temperature": temperature,
        "thinking_config": build_thinking_config(thinking_level),
    }
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if response_mime_type:
        config_kwargs["response_mime_type"] = response_mime_type
    if response_schema is not None:
        config_kwargs["response_schema"] = response_schema
        config_kwargs.setdefault("response_mime_type", "application/json")

    gen_config = types.GenerateContentConfig(**config_kwargs)

    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=gen_config,
            )
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries and _is_rate_limit_or_transient(exc):
                delay = min(8.0, 1.5 * (2**attempt))
                logger.warning(
                    "Transient Gemini error (%s) on attempt %d/%d; retrying in %.1fs",
                    model,
                    attempt + 1,
                    max_retries + 1,
                    delay,
                )
                time.sleep(delay)
                continue
            if _is_hard_quota_error(exc):
                raise QuotaExhaustedError(
                    "Gemini API quota exceeded. Please check your plan and billing details at "
                    "https://ai.google.dev/gemini-api/docs/rate-limits or try again later."
                ) from exc
            raise

    assert last_exc is not None
    raise last_exc
