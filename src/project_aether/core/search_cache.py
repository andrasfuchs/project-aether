"""
Cache utilities for patent search results.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_aether.core.config import get_config


CACHE_VERSION = 1
CACHE_EXPIRATION_DAYS = 30

import logging

logger = logging.getLogger("ProjectAether")


def _utc_now() -> datetime:
    return datetime.utcnow()


def get_search_cache_path() -> Path:
    """Get the search cache file path."""
    config = get_config()
    return config.database_path.parent / "search_cache.json"


def _empty_search_cache() -> Dict[str, Any]:
    """Create an empty search cache structure."""
    return {
        "version": CACHE_VERSION,
        "entries": {},
        "updated_at": _utc_now().isoformat(),
    }


def load_search_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the search cache from disk.
    
    Args:
        path: Optional custom cache file path.
        
    Returns:
        Cache dictionary with version, entries, and metadata.
    """
    cache_path = path or get_search_cache_path()
    if not cache_path.exists():
        return _empty_search_cache()

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("entries", {})
        data.setdefault("version", CACHE_VERSION)
        data.setdefault("updated_at", _utc_now().isoformat())
        return data
    except Exception:
        return _empty_search_cache()


def save_search_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Save the search cache to disk.
    
    Args:
        cache: Cache dictionary to save.
        path: Optional custom cache file path.
    """
    cache_path = path or get_search_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now().isoformat()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def _make_cache_key(
    jurisdiction: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    positive_keywords: Optional[List[str]],
    negative_keywords: Optional[List[str]],
    patent_status_filter: Optional[List[str]],
    language: str,
    limit: Optional[int],
) -> str:
    """Generate a unique cache key from search parameters.
    
    All search parameters are included in the key to ensure cache hits
    only occur when ALL parameters match exactly.
    
    Args:
        jurisdiction: Single jurisdiction code or None.
        start_date: Start date in YYYY-MM-DD or None.
        end_date: End date in YYYY-MM-DD or None.
        positive_keywords: List of include terms or None.
        negative_keywords: List of exclude terms or None.
        patent_status_filter: List of status filters or None.
        language: Language code (e.g., "EN", "ZH").
        limit: Maximum number of results or None.
        
    Returns:
        SHA-256 hash string as cache key.
    """
    # Normalize lists to sorted tuples for consistent hashing
    pos_kw = tuple(sorted(positive_keywords)) if positive_keywords else ()
    neg_kw = tuple(sorted(negative_keywords)) if negative_keywords else ()
    status = tuple(sorted(patent_status_filter)) if patent_status_filter else ()
    
    # Build a canonical representation of all parameters
    payload = json.dumps(
        {
            "jurisdiction": jurisdiction,
            "start_date": start_date,
            "end_date": end_date,
            "positive_keywords": pos_kw,
            "negative_keywords": neg_kw,
            "patent_status_filter": status,
            "language": language,
            "limit": limit,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _is_cache_entry_expired(cached_at: str) -> bool:
    """Check if a cache entry has expired based on the cached timestamp.
    
    Args:
        cached_at: ISO format timestamp string when entry was cached.
        
    Returns:
        True if entry is older than CACHE_EXPIRATION_DAYS, False otherwise.
    """
    try:
        cached_time = datetime.fromisoformat(cached_at)
        age = _utc_now() - cached_time
        return age > timedelta(days=CACHE_EXPIRATION_DAYS)
    except (ValueError, TypeError):
        # If we can't parse the timestamp, treat as expired
        return True


def get_cached_search_results(
    cache: Dict[str, Any],
    jurisdiction: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    positive_keywords: Optional[List[str]],
    negative_keywords: Optional[List[str]],
    patent_status_filter: Optional[List[str]],
    language: str,
    limit: Optional[int],
) -> Optional[Dict[str, Any]]:
    """Retrieve cached search results if available and not expired.
    
    Args:
        cache: The search cache dictionary.
        jurisdiction: Single jurisdiction code or None.
        start_date: Start date in YYYY-MM-DD or None.
        end_date: End date in YYYY-MM-DD or None.
        positive_keywords: List of include terms or None.
        negative_keywords: List of exclude terms or None.
        patent_status_filter: List of status filters or None.
        language: Language code (e.g., "EN", "ZH").
        limit: Maximum number of results or None.
        
    Returns:
        Cached search results dictionary if found and valid, None otherwise.
    """
    cache_key = _make_cache_key(
        jurisdiction=jurisdiction,
        start_date=start_date,
        end_date=end_date,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        patent_status_filter=patent_status_filter,
        language=language,
        limit=limit,
    )
    
    entries = cache.get("entries", {})
    entry = entries.get(cache_key)
    
    if entry is None:
        return None
    
    # Check if entry has expired
    cached_at = entry.get("cached_at")
    if cached_at and _is_cache_entry_expired(cached_at):
        # Remove expired entry
        del entries[cache_key]
        return None
    
    return entry.get("results")


def set_cached_search_results(
    cache: Dict[str, Any],
    jurisdiction: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
    positive_keywords: Optional[List[str]],
    negative_keywords: Optional[List[str]],
    patent_status_filter: Optional[List[str]],
    language: str,
    limit: Optional[int],
    results: Dict[str, Any],
) -> None:
    """Store search results in the cache.
    
    Args:
        cache: The search cache dictionary.
        jurisdiction: Single jurisdiction code or None.
        start_date: Start date in YYYY-MM-DD or None.
        end_date: End date in YYYY-MM-DD or None.
        positive_keywords: List of include terms or None.
        negative_keywords: List of exclude terms or None.
        patent_status_filter: List of status filters or None.
        language: Language code (e.g., "EN", "ZH").
        limit: Maximum number of results or None.
        results: Search results dictionary to cache.
    """
    cache_key = _make_cache_key(
        jurisdiction=jurisdiction,
        start_date=start_date,
        end_date=end_date,
        positive_keywords=positive_keywords,
        negative_keywords=negative_keywords,
        patent_status_filter=patent_status_filter,
        language=language,
        limit=limit,
    )
    
    entries = cache.setdefault("entries", {})
    entry = {
        "cached_at": _utc_now().isoformat(),
        "parameters": {
            "jurisdiction": jurisdiction,
            "start_date": start_date,
            "end_date": end_date,
            "positive_keywords": positive_keywords,
            "negative_keywords": negative_keywords,
            "patent_status_filter": patent_status_filter,
            "language": language,
            "limit": limit,
        },
        "results": results,
    }
    entries[cache_key] = entry


def clean_expired_entries(cache: Dict[str, Any]) -> int:
    """Remove all expired entries from the cache.
    
    Args:
        cache: The search cache dictionary.
        
    Returns:
        Number of expired entries removed.
    """
    entries = cache.get("entries", {})
    expired_keys = []
    
    for key, entry in entries.items():
        cached_at = entry.get("cached_at")
        if cached_at and _is_cache_entry_expired(cached_at):
            expired_keys.append(key)
    
    for key in expired_keys:
        del entries[key]
    
    return len(expired_keys)
