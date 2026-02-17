"""
Cache utilities for LLM scoring results.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from project_aether.core.config import get_config


CACHE_VERSION = 1


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def get_scoring_cache_path() -> Path:
    config = get_config()
    return config.database_path.parent / "scoring_cache.json"


def _empty_scoring_cache() -> Dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "entries": {},
        "updated_at": _utc_now(),
    }


def load_scoring_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    cache_path = path or get_scoring_cache_path()
    if not cache_path.exists():
        return _empty_scoring_cache()

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("entries", {})
        data.setdefault("version", CACHE_VERSION)
        data.setdefault("updated_at", _utc_now())
        return data
    except Exception:
        return _empty_scoring_cache()


def save_scoring_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    cache_path = path or get_scoring_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def _make_cache_key(
    title: str,
    abstract: str,
    system_message: str,
    model: str,
) -> str:
    payload = "\n".join([
        (title or "").strip(),
        (abstract or "").strip(),
        (system_message or "").strip(),
        (model or "").strip(),
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_cached_score(
    cache: Dict[str, Any],
    title: str,
    abstract: str,
    system_message: str,
    model: str,
) -> Optional[Dict[str, Any]]:
    cache_key = _make_cache_key(title, abstract, system_message, model)
    return cache.get("entries", {}).get(cache_key)


def set_cached_score(
    cache: Dict[str, Any],
    record_id: str,
    title: str,
    abstract: str,
    system_message: str,
    model: str,
    score: float,
    tags: list[str],
    features: list[str],
) -> Dict[str, Any]:
    cache_key = _make_cache_key(title, abstract, system_message, model)
    entries = cache.setdefault("entries", {})
    entry = {
        "record_id": record_id,
        "title": title,
        "abstract": abstract,
        "system_message": system_message,
        "model": model,
        "score": score,
        "tags": tags,
        "features": features,
        "scored_at": _utc_now(),
    }
    entries[cache_key] = entry
    return entry
