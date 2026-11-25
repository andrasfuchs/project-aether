"""
Keyword translation and caching utilities.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from project_aether.core.config import get_config
from project_aether.core.llm import DEFAULT_LLM_MODEL, generate_content

CACHE_VERSION = 1
DEFAULT_MODEL = DEFAULT_LLM_MODEL


class KeywordTranslationResponse(BaseModel):
    include: list[list[str]]
    exclude: list[str]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_cache_path() -> Path:
    config = get_config()
    return config.database_path.parent / "keyword_cache.json"


def _empty_cache() -> dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "keyword_sets": {},
        "history": [],
        "translations": {},
        "updated_at": _utc_now(),
    }


def load_keyword_cache(path: Path | None = None) -> dict[str, Any]:
    cache_path = path or get_cache_path()
    if not cache_path.exists():
        return _empty_cache()

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        for key in ("keyword_sets", "history", "translations"):
            data.setdefault(key, {} if key != "history" else [])
        data.setdefault("version", CACHE_VERSION)
        data.setdefault("updated_at", _utc_now())
        return data
    except Exception:
        return _empty_cache()


def save_keyword_cache(cache: dict[str, Any], path: Path | None = None) -> None:
    cache_path = path or get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def normalize_terms(terms: list[str]) -> list[str]:
    seen = set()
    output: list[str] = []
    for term in terms:
        cleaned = (term or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output


def normalize_include_terms(terms: list[Any]) -> list[list[str]]:
    normalized: list[list[str]] = []
    for item in terms:
        if isinstance(item, list):
            group = normalize_terms([str(t) for t in item])
            if group:
                normalized.append(group)
        elif isinstance(item, str):
            t = item.strip()
            if t:
                normalized.append([t])
    return normalized


def keyword_set_id(include_terms: list[list[str]], exclude_terms: list[str]) -> str:
    normalized_include = []
    for group in normalize_include_terms(include_terms):
        normalized_include.append(",".join(sorted(set(group))))
    normalized = "|".join(sorted(normalized_include))
    normalized += "||" + "|".join(sorted(set(normalize_terms(exclude_terms))))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def ensure_keyword_set(
    cache: dict[str, Any],
    include_terms: list[list[str]],
    exclude_terms: list[str],
    label: str | None = None,
) -> dict[str, Any]:
    set_id = keyword_set_id(include_terms, exclude_terms)
    keyword_sets = cache.setdefault("keyword_sets", {})

    if set_id not in keyword_sets:
        keyword_sets[set_id] = {
            "id": set_id,
            "label": label or f"Keyword Set {set_id}",
            "include": normalize_include_terms(include_terms),
            "exclude": normalize_terms(exclude_terms),
            "created_at": _utc_now(),
        }

    _touch_history(cache, set_id)
    return keyword_sets[set_id]


def _touch_history(cache: dict[str, Any], set_id: str, max_items: int = 25) -> None:
    history = cache.setdefault("history", [])
    history = [entry for entry in history if entry.get("id") != set_id]
    history.insert(0, {"id": set_id, "last_used": _utc_now()})
    cache["history"] = history[:max_items]


def get_history_entries(cache: dict[str, Any]) -> list[dict[str, Any]]:
    keyword_sets = cache.get("keyword_sets", {})
    entries = []
    for item in cache.get("history", []):
        set_id = item.get("id")
        if set_id in keyword_sets:
            entry = {**keyword_sets[set_id]}
            entry["last_used"] = item.get("last_used")
            entries.append(entry)
    return entries


def delete_keyword_set(cache: dict[str, Any], set_id: str) -> None:
    cache.get("keyword_sets", {}).pop(set_id, None)
    cache["translations"] = {
        key: value
        for key, value in cache.get("translations", {}).items()
        if key != set_id
    }
    cache["history"] = [
        entry for entry in cache.get("history", []) if entry.get("id") != set_id
    ]


def get_cached_translation(
    cache: dict[str, Any],
    set_id: str,
    language: str,
) -> dict[str, Any] | None:
    return cache.get("translations", {}).get(set_id, {}).get(language)


def set_cached_translation(
    cache: dict[str, Any],
    set_id: str,
    language: str,
    include_terms: list[list[str]],
    exclude_terms: list[str],
    source: str,
    model: str | None = None,
) -> dict[str, Any]:
    translations = cache.setdefault("translations", {})
    set_translations = translations.setdefault(set_id, {})
    entry = {
        "language": language,
        "include": normalize_include_terms(include_terms),
        "exclude": normalize_terms(exclude_terms),
        "source": source,
        "updated_at": _utc_now(),
    }
    if model:
        entry["model"] = model
    set_translations[language] = entry
    return entry


def translate_keywords_with_llm(
    include_terms: list[list[str]],
    exclude_terms: list[str],
    target_language: str,
    context: str,
    api_key: str,
    model: str | None = None,
    thinking_level: str | None = None,
) -> tuple[list[list[str]], list[str]]:
    if not include_terms and not exclude_terms:
        return [], []

    config = get_config()
    chosen_model = model or config.llm_keyword_model
    chosen_thinking = thinking_level or config.llm_keyword_thinking_level

    system_prompt = (
        f"You are translating short patent search keyword phrases for a technical "
        f"prior-art query to {target_language}. "
        "Preserve acronyms (e.g., LENR, LANR), chemical symbols, "
        "and established domain terms. Keep phrases concise, natural for patent "
        "titles and abstracts, and avoid duplicate translations within a synonym group. "
        "Maintain the exact list-of-lists structure for `include` and list structure for `exclude`."
    )

    payload = {
        "target_language": target_language,
        "context": context,
        "include_terms": include_terms,
        "exclude_terms": exclude_terms,
    }

    response = generate_content(
        api_key=api_key,
        model=chosen_model,
        contents=json.dumps(payload, ensure_ascii=False),
        system_instruction=system_prompt,
        temperature=0.2,
        thinking_level=chosen_thinking,
        response_schema=KeywordTranslationResponse,
        response_mime_type="application/json",
    )

    data = _extract_json(response.text or "")
    include = normalize_include_terms(data.get("include", include_terms))
    exclude = normalize_terms(data.get("exclude", exclude_terms))
    return include, exclude


def _extract_json(text: str) -> dict[str, Any]:
    if not isinstance(text, str):
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
    return {}
