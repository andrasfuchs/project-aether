"""
Per-query JSON file cache utilities for patent search results.
Each cached query is stored as a standalone readable JSON file under `data/search_cache/`.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from project_aether.core.config import get_config

CACHE_VERSION = 2
CACHE_EXPIRATION_DAYS = 30

logger = logging.getLogger("ProjectAether.SearchCache")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def get_search_cache_dir() -> Path:
    """Return directory storing per-query search cache JSON files."""
    config = get_config()
    return config.database_path.parent / "search_cache"


def _legacy_search_cache_path(cache_dir: Path) -> Path:
    return cache_dir.parent / "search_cache.json"


def _migrate_legacy_search_cache(cache_dir: Path) -> None:
    """Split legacy monolithic `search_cache.json` into per-query JSON files once."""
    legacy_path = _legacy_search_cache_path(cache_dir)
    if not legacy_path.exists() or cache_dir.exists():
        return
    try:
        with legacy_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        entries = data.get("entries", {})
        if not isinstance(entries, dict) or not entries:
            return
        cache_dir.mkdir(parents=True, exist_ok=True)
        migrated = 0
        for entry in entries.values():
            if not isinstance(entry, dict):
                continue
            cached_at = entry.get("cached_at")
            if cached_at and _is_cache_entry_expired(cached_at):
                continue
            params = entry.get("parameters", {})
            key = _make_cache_key(
                provider=params.get("provider"),
                jurisdiction=params.get("jurisdiction"),
                start_date=params.get("start_date"),
                end_date=params.get("end_date"),
                positive_keywords=params.get("positive_keywords"),
                negative_keywords=params.get("negative_keywords"),
                patent_status_filter=params.get("patent_status_filter"),
                language=params.get("language") or "EN",
                limit=params.get("limit"),
            )
            file_path = _entry_file_path(
                cache_dir,
                provider=params.get("provider"),
                language=params.get("language") or "EN",
                cache_key=key,
            )
            with file_path.open("w", encoding="utf-8") as out:
                json.dump(entry, out, indent=2, ensure_ascii=False)
            migrated += 1
        logger.info("Migrated %d search cache entries to %s", migrated, cache_dir)
    except Exception as exc:
        logger.warning("Failed to migrate legacy search cache: %s", exc)


def _make_cache_key(
    provider: str | None,
    jurisdiction: str | None,
    start_date: str | None,
    end_date: str | None,
    positive_keywords: list[Any] | None,
    negative_keywords: list[str] | None,
    patent_status_filter: list[str] | None,
    language: str,
    limit: int | None,
) -> str:
    """Generate a unique cache key from search parameters.

    When `start_date` is None (unbounded search), `end_date` is omitted from the
    key so repeated unbounded searches reuse cached results across days.
    """
    pos_kw_normalized: list[Any] = []
    if positive_keywords:
        for item in positive_keywords:
            if isinstance(item, list):
                pos_kw_normalized.append(tuple(sorted(str(t) for t in item)))
            else:
                pos_kw_normalized.append(str(item))
    pos_kw = tuple(sorted(pos_kw_normalized, key=lambda x: str(x)))

    neg_kw = tuple(sorted(negative_keywords)) if negative_keywords else ()
    status = tuple(sorted(patent_status_filter)) if patent_status_filter else ()

    effective_end_date = end_date if start_date is not None else None

    payload = json.dumps(
        {
            "provider": provider,
            "jurisdiction": jurisdiction,
            "start_date": start_date,
            "end_date": effective_end_date,
            "positive_keywords": pos_kw,
            "negative_keywords": neg_kw,
            "patent_status_filter": status,
            "language": language,
            "limit": limit,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _entry_file_path(
    cache_dir: Path,
    *,
    provider: str | None,
    language: str,
    cache_key: str,
) -> Path:
    prov = (provider or "any").lower()
    lang = (language or "EN").upper()
    return cache_dir / f"{prov}_{lang}_{cache_key[:16]}.json"


def _is_cache_entry_expired(cached_at: str) -> bool:
    try:
        cached_time = datetime.fromisoformat(cached_at)
        if cached_time.tzinfo is None:
            cached_time = cached_time.replace(tzinfo=UTC)
        return (_utc_now() - cached_time) > timedelta(days=CACHE_EXPIRATION_DAYS)
    except (ValueError, TypeError):
        return True


def load_search_cache(cache_dir: Path | None = None) -> dict[str, Any]:
    """Return a lightweight handle for the per-query search cache directory."""
    target_dir = cache_dir or get_search_cache_dir()
    if cache_dir is None:
        _migrate_legacy_search_cache(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    return {"version": CACHE_VERSION, "dir": str(target_dir)}


def save_search_cache(cache: dict[str, Any], cache_dir: Path | None = None) -> None:
    """No-op compatibility helper; per-query files are written directly on set."""
    _ = cache, cache_dir


def get_cached_search_results(
    cache: dict[str, Any],
    provider: str | None,
    jurisdiction: str | None,
    start_date: str | None,
    end_date: str | None,
    positive_keywords: list[Any] | None,
    negative_keywords: list[str] | None,
    patent_status_filter: list[str] | None,
    language: str,
    limit: int | None,
) -> dict[str, Any] | None:
    """Retrieve cached search results for exact query parameters if not expired."""
    target_dir = Path(cache.get("dir") or get_search_cache_dir())
    cache_key = _make_cache_key(
        provider=provider,
        jurisdiction=jurisdiction,
        start_date=start_date,
        end_date=end_date,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        patent_status_filter=patent_status_filter,
        language=language,
        limit=limit,
    )
    file_path = _entry_file_path(target_dir, provider=provider, language=language, cache_key=cache_key)
    if not file_path.exists():
        return None

    try:
        with file_path.open("r", encoding="utf-8") as handle:
            entry = json.load(handle)
    except Exception:
        return None

    cached_at = entry.get("cached_at")
    if cached_at and _is_cache_entry_expired(cached_at):
        try:
            file_path.unlink()
        except OSError:
            pass
        return None

    return entry.get("results")


def set_cached_search_results(
    cache: dict[str, Any],
    provider: str | None,
    jurisdiction: str | None,
    start_date: str | None,
    end_date: str | None,
    positive_keywords: list[Any] | None,
    negative_keywords: list[str] | None,
    patent_status_filter: list[str] | None,
    language: str,
    limit: int | None,
    results: dict[str, Any],
) -> None:
    """Persist a single query's search results to its own JSON file."""
    target_dir = Path(cache.get("dir") or get_search_cache_dir())
    target_dir.mkdir(parents=True, exist_ok=True)
    cache_key = _make_cache_key(
        provider=provider,
        jurisdiction=jurisdiction,
        start_date=start_date,
        end_date=end_date,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        patent_status_filter=patent_status_filter,
        language=language,
        limit=limit,
    )
    file_path = _entry_file_path(target_dir, provider=provider, language=language, cache_key=cache_key)
    entry = {
        "cached_at": _utc_now().isoformat(),
        "parameters": {
            "provider": provider,
            "jurisdiction": jurisdiction,
            "start_date": start_date,
            "end_date": end_date if start_date is not None else None,
            "positive_keywords": positive_keywords,
            "negative_keywords": negative_keywords,
            "patent_status_filter": patent_status_filter,
            "language": language,
            "limit": limit,
        },
        "results": results,
    }
    with file_path.open("w", encoding="utf-8") as handle:
        json.dump(entry, handle, indent=2, ensure_ascii=False)


def clean_expired_entries(cache: dict[str, Any]) -> int:
    """Remove expired per-query JSON files from the cache directory."""
    target_dir = Path(cache.get("dir") or get_search_cache_dir())
    if not target_dir.exists():
        return 0
    removed = 0
    for file_path in target_dir.glob("*.json"):
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                entry = json.load(handle)
            cached_at = entry.get("cached_at")
            if cached_at and _is_cache_entry_expired(cached_at):
                file_path.unlink()
                removed += 1
        except Exception as exc:
            logger.debug("Skipping unreadable search cache file %s: %s", file_path, exc)
            continue
    return removed


def clear_search_cache(cache_dir: Path | None = None) -> int:
    """Delete all per-query search cache files and return count removed."""
    target_dir = cache_dir or get_search_cache_dir()
    if not target_dir.exists():
        return 0
    removed = 0
    for file_path in target_dir.glob("*.json"):
        try:
            file_path.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def get_search_cache_stats(cache_dir: Path | None = None) -> dict[str, Any]:
    """Return file count and total size in bytes for the search cache directory."""
    target_dir = cache_dir or get_search_cache_dir()
    if not target_dir.exists():
        return {"entries": 0, "size_bytes": 0, "path": str(target_dir)}
    files = list(target_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files if f.exists())
    return {"entries": len(files), "size_bytes": total_size, "path": str(target_dir)}
