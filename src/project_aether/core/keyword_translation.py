"""
Keyword translation and caching utilities.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import types

from project_aether.core.config import get_config
from project_aether.core.keywords import DEFAULT_KEYWORDS


CACHE_VERSION = 1
DEFAULT_MODEL = "gemini-3-flash-preview"


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def get_cache_path() -> Path:
    config = get_config()
    return config.database_path.parent / "keyword_cache.json"


def _empty_cache() -> Dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "keyword_sets": {},
        "history": [],
        "translations": {},
        "updated_at": _utc_now(),
    }


def load_keyword_cache(path: Optional[Path] = None) -> Dict[str, Any]:
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


def save_keyword_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    cache_path = path or get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def normalize_terms(terms: List[str]) -> List[str]:
    return [term.strip() for term in terms if term and term.strip()]


def keyword_set_id(include_terms: List[str], exclude_terms: List[str]) -> str:
    normalized = "|".join(sorted(set(normalize_terms(include_terms))))
    normalized += "||" + "|".join(sorted(set(normalize_terms(exclude_terms))))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def ensure_keyword_set(
    cache: Dict[str, Any],
    include_terms: List[str],
    exclude_terms: List[str],
    label: Optional[str] = None,
) -> Dict[str, Any]:
    set_id = keyword_set_id(include_terms, exclude_terms)
    keyword_sets = cache.setdefault("keyword_sets", {})

    if set_id not in keyword_sets:
        keyword_sets[set_id] = {
            "id": set_id,
            "label": label or f"Keyword Set {set_id}",
            "include": normalize_terms(include_terms),
            "exclude": normalize_terms(exclude_terms),
            "created_at": _utc_now(),
        }

    _touch_history(cache, set_id)
    return keyword_sets[set_id]


def _touch_history(cache: Dict[str, Any], set_id: str, max_items: int = 25) -> None:
    history = cache.setdefault("history", [])
    history = [entry for entry in history if entry.get("id") != set_id]
    history.insert(0, {"id": set_id, "last_used": _utc_now()})
    cache["history"] = history[:max_items]


def get_history_entries(cache: Dict[str, Any]) -> List[Dict[str, Any]]:
    keyword_sets = cache.get("keyword_sets", {})
    entries = []
    for item in cache.get("history", []):
        set_id = item.get("id")
        if set_id in keyword_sets:
            entry = {**keyword_sets[set_id]}
            entry["last_used"] = item.get("last_used")
            entries.append(entry)
    return entries


def delete_keyword_set(cache: Dict[str, Any], set_id: str) -> None:
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
    cache: Dict[str, Any],
    set_id: str,
    language: str,
) -> Optional[Dict[str, Any]]:
    return cache.get("translations", {}).get(set_id, {}).get(language)


def set_cached_translation(
    cache: Dict[str, Any],
    set_id: str,
    language: str,
    include_terms: List[str],
    exclude_terms: List[str],
    source: str,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    translations = cache.setdefault("translations", {})
    set_translations = translations.setdefault(set_id, {})
    entry = {
        "language": language,
        "include": normalize_terms(include_terms),
        "exclude": normalize_terms(exclude_terms),
        "source": source,
        "updated_at": _utc_now(),
    }
    if model:
        entry["model"] = model
    set_translations[language] = entry
    return entry


def default_translation_for_language(
    language: str,
) -> Optional[Tuple[List[str], List[str]]]:
    block = DEFAULT_KEYWORDS.get(language)
    if not block:
        return None
    return (
        normalize_terms(block.get("positive", [])),
        normalize_terms(block.get("negative", [])),
    )


def translate_keywords_with_llm(
    include_terms: List[str],
    exclude_terms: List[str],
    target_language: str,
    context: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> Tuple[List[str], List[str]]:
    if not include_terms and not exclude_terms:
        return [], []

    system_prompt = (
        "You are translating short patent search keyword phrases for a technical "
        "prior-art query to " + target_language + ". "
        "Preserve acronyms (e.g., LENR, LANR), chemical symbols, "
        "and established domain terms. Keep phrases concise, natural for patent "
        "abstracts, and avoid adding commentary."
        "Your input is a JSON object with 'include_terms' and 'exclude_terms' lists."
        "Translate those list items and return them as a strict JSON output."
    )

    payload = {
        "target_language": target_language,
        "context": context,
        "include_terms": include_terms,
        "exclude_terms": exclude_terms,
        "output_format": {
            "include": ["..."],
            "exclude": ["..."]
        },
    }

    # Initialize Google GenAI client
    client = genai.Client(api_key=api_key)
    
    # Generate content with Gemini using proper configuration
    response = client.models.generate_content(
        model=model,
        contents=json.dumps(payload, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=1.0,  # Recommended default for Gemini 3 models
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            )
        )
    )

    # Extract text from response
    content = response.text or ""
    
    data = _extract_json(content)
    include = normalize_terms(data.get("include", include_terms))
    exclude = normalize_terms(data.get("exclude", exclude_terms))
    return include, exclude


def _extract_json(text: str) -> Dict[str, Any]:
    if not isinstance(text, str):
        return {}
    
    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}
    return {}


# Backward compatibility wrappers for abstract translation functions
# These now delegate to the general translation_service module
from project_aether.core.translation_service import (
    load_translation_cache as _load_translation_cache,
    save_translation_cache as _save_translation_cache,
    get_cached_translation as _get_translation,
    set_cached_translation as _set_translation,
    translate_text as _translate_text,
)


def get_abstract_cache_path() -> Path:
    """Deprecated: Use translation_service.get_translation_cache_path() instead."""
    config = get_config()
    return config.database_path.parent / "abstract_cache.json"


def load_abstract_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Deprecated: Use translation_service.load_translation_cache() instead.
    Loads from the new translation_cache.json for consistency.
    """
    return _load_translation_cache()


def save_abstract_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    """
    Deprecated: Use translation_service.save_translation_cache() instead.
    """
    _save_translation_cache(cache)


def get_cached_abstract_translation(
    cache: Dict[str, Any],
    lens_id: str,
    target_language: str,
) -> Optional[str]:
    """
    Deprecated: Use translation_service.get_cached_translation() instead.
    Wrapper that maintains old API (assumes source language is English).
    """
    return _get_translation(cache, lens_id, "English", target_language)


def set_cached_abstract_translation(
    cache: Dict[str, Any],
    lens_id: str,
    target_language: str,
    translated_text: str,
    model: str = DEFAULT_MODEL,
) -> None:
    """
    Deprecated: Use translation_service.set_cached_translation() instead.
    Wrapper that maintains old API (assumes source language is English).
    """
    _set_translation(cache, lens_id, "English", target_language, translated_text, model)


def translate_text_with_llm(
    text: str,
    target_language: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Deprecated: Use translation_service.translate_text() instead.
    Wrapper that maintains old API (assumes source language is English).
    """
    return _translate_text(text, "English", target_language, api_key, model)