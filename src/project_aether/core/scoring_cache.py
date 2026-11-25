"""
Append-only JSONL cache utilities for LLM patent scoring results.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from project_aether.core.config import get_config

logger = logging.getLogger("ProjectAether.ScoringCache")

CACHE_VERSION = 3
_FILE_LOCK = threading.Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_scoring_cache_path() -> Path:
    """Return path to the JSONL scoring cache file."""
    config = get_config()
    return config.database_path.parent / "scoring_cache.jsonl"


def _legacy_scoring_cache_path(jsonl_path: Path) -> Path:
    return jsonl_path.with_suffix(".json")


def _empty_scoring_cache() -> dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "entries": {},
        "updated_at": _utc_now(),
    }


def make_score_cache_key(
    record_id: str,
    title: str,
    abstract: str,
    system_message: str,
    model: str,
    thinking_level: str = "low",
) -> str:
    """Build a deterministic cache key sensitive to record, text, prompt, model, and effort."""
    rid = (record_id or "").strip()
    prompt_hash = hashlib.sha256((system_message or "").encode("utf-8")).hexdigest()[:16]
    text_hash = hashlib.sha256(f"{title}\n{abstract}".encode()).hexdigest()[:16]
    payload = f"{rid}|{model}|{thinking_level}|{prompt_hash}|{text_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _migrate_legacy_json(legacy_path: Path, jsonl_path: Path) -> None:
    """Migrate legacy `scoring_cache.json` entries into `scoring_cache.jsonl` once."""
    if not legacy_path.exists() or jsonl_path.exists():
        return
    try:
        with legacy_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        legacy_entries = data.get("entries_by_record_id", {})
        if not isinstance(legacy_entries, dict) or not legacy_entries:
            return

        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as out:
            for rid, entry in legacy_entries.items():
                if not isinstance(entry, dict):
                    continue
                model = str(entry.get("model") or "unknown")
                thinking_level = str(entry.get("thinking_level") or "low")
                title = str(entry.get("title") or "")
                abstract = str(entry.get("abstract") or "")
                system_message = str(entry.get("system_message") or "")
                cache_key = make_score_cache_key(
                    rid, title, abstract, system_message, model, thinking_level
                )
                record = {
                    **entry,
                    "record_id": rid,
                    "thinking_level": thinking_level,
                    "cache_key": cache_key,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Migrated %d legacy scoring cache entries to %s", len(legacy_entries), jsonl_path)
    except Exception as exc:
        logger.warning("Failed to migrate legacy scoring cache: %s", exc)


def load_scoring_cache(path: Path | None = None) -> dict[str, Any]:
    """Load scoring cache from JSONL into memory."""
    cache_path = path or get_scoring_cache_path()
    if path is None:
        _migrate_legacy_json(_legacy_scoring_cache_path(cache_path), cache_path)

    cache = _empty_scoring_cache()
    if not cache_path.exists():
        return cache

    entries = cache["entries"]
    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                key = entry.get("cache_key")
                if not key:
                    key = make_score_cache_key(
                        str(entry.get("record_id") or ""),
                        str(entry.get("title") or ""),
                        str(entry.get("abstract") or ""),
                        str(entry.get("system_message") or ""),
                        str(entry.get("model") or ""),
                        str(entry.get("thinking_level") or "low"),
                    )
                    entry["cache_key"] = key
                entries[key] = entry
    except Exception as exc:
        logger.warning("Failed to load scoring cache %s: %s", cache_path, exc)
    return cache


def save_scoring_cache(cache: dict[str, Any], path: Path | None = None) -> None:
    """Rewrite the full scoring cache JSONL (used for compaction/cleanup)."""
    cache_path = path or get_scoring_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    entries = cache.get("entries", {})
    with _FILE_LOCK, cache_path.open("w", encoding="utf-8") as handle:
        for entry in entries.values():
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    cache["updated_at"] = _utc_now()


def get_cached_score(
    cache: dict[str, Any],
    record_id: str,
    title: str,
    abstract: str,
    system_message: str,
    model: str,
    thinking_level: str = "low",
) -> dict[str, Any] | None:
    """Retrieve a cached score matching record, text, prompt, model, and thinking level."""
    rid = (record_id or "").strip()
    if not rid:
        return None
    key = make_score_cache_key(rid, title, abstract, system_message, model, thinking_level)
    entry = cache.get("entries", {}).get(key)
    return entry if isinstance(entry, dict) else None


def set_cached_score(
    cache: dict[str, Any],
    record_id: str,
    title: str,
    abstract: str,
    system_message: str,
    model: str,
    score: float,
    tags: list[str],
    features: list[str],
    *,
    thinking_level: str = "low",
    title_en: str | None = None,
    domain_category: str | None = None,
    rationale: str | None = None,
    append_path: Path | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Store a score in memory and optionally append one JSONL line to disk."""
    rid = (record_id or "").strip()
    key = make_score_cache_key(rid, title, abstract, system_message, model, thinking_level)
    entry: dict[str, Any] = {
        "cache_key": key,
        "record_id": rid,
        "title": title,
        "abstract": abstract,
        "system_message": system_message,
        "model": model,
        "thinking_level": thinking_level,
        "score": score,
        "title_en": title_en,
        "domain_category": domain_category,
        "tags": tags,
        "features": features,
        "rationale": rationale,
        "scored_at": _utc_now(),
    }
    cache.setdefault("entries", {})[key] = entry
    cache["updated_at"] = _utc_now()

    if persist:
        target_path = append_path or get_scoring_cache_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with _FILE_LOCK, target_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return entry


def clear_scoring_cache(path: Path | None = None) -> int:
    """Delete the scoring cache file and return number of entries cleared."""
    cache_path = path or get_scoring_cache_path()
    count = len(load_scoring_cache(cache_path).get("entries", {}))
    with _FILE_LOCK:
        if cache_path.exists():
            cache_path.unlink()
    return count


def get_scoring_cache_stats(path: Path | None = None) -> dict[str, Any]:
    """Return entry count and file size in bytes for diagnostics."""
    cache_path = path or get_scoring_cache_path()
    size_bytes = cache_path.stat().st_size if cache_path.exists() else 0
    count = len(load_scoring_cache(cache_path).get("entries", {}))
    return {"entries": count, "size_bytes": size_bytes, "path": str(cache_path)}
