"""
General-purpose translation service for patent documents and abstracts.
Stores cached translations in an append-only JSONL file for fast, inspectable persistence.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from project_aether.core.config import get_config
from project_aether.core.llm import DEFAULT_LLM_MODEL, generate_content

logger = logging.getLogger("TranslationService")

CACHE_VERSION = 2
DEFAULT_MODEL = DEFAULT_LLM_MODEL
MAX_CONCURRENT_TRANSLATIONS = 10

_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TRANSLATIONS)
_cache_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def get_translation_cache_path() -> Path:
    """Get the path to the JSONL translation cache file."""
    config = get_config()
    return config.database_path.parent / "translation_cache.jsonl"


def _legacy_translation_cache_path(jsonl_path: Path) -> Path:
    return jsonl_path.with_suffix(".json")


def _empty_translation_cache() -> dict[str, Any]:
    return {
        "version": CACHE_VERSION,
        "translations": {},
        "updated_at": _utc_now(),
    }


def _migrate_legacy_translation_cache(legacy_path: Path, jsonl_path: Path) -> None:
    """Migrate legacy `translation_cache.json` entries into `translation_cache.jsonl` once."""
    if not legacy_path.exists() or jsonl_path.exists():
        return
    try:
        with legacy_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        translations = data.get("translations", {})
        if not isinstance(translations, dict) or not translations:
            return
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as out:
            for cache_key, entry in translations.items():
                if not isinstance(entry, dict):
                    continue
                record = {"cache_key": cache_key, **entry}
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Migrated %d translation cache entries to %s", len(translations), jsonl_path)
    except Exception as exc:
        logger.warning("Failed to migrate legacy translation cache: %s", exc)


def load_translation_cache(path: Path | None = None) -> dict[str, Any]:
    """Load the translation cache from JSONL."""
    cache_path = path or get_translation_cache_path()
    if path is None:
        _migrate_legacy_translation_cache(_legacy_translation_cache_path(cache_path), cache_path)

    cache = _empty_translation_cache()
    if not cache_path.exists():
        return cache

    translations = cache["translations"]
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
                key = entry.get("cache_key") or _make_cache_key(
                    str(entry.get("source_id") or ""),
                    str(entry.get("source_language") or ""),
                    str(entry.get("target_language") or ""),
                )
                entry["cache_key"] = key
                translations[key] = entry
    except Exception as exc:
        logger.warning("Failed to load translation cache %s: %s", cache_path, exc)
    return cache


def save_translation_cache(cache: dict[str, Any], path: Path | None = None) -> None:
    """Rewrite the full translation cache JSONL (for compaction/cleanup)."""
    cache_path = path or get_translation_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    translations = cache.get("translations", {})
    with _cache_lock, cache_path.open("w", encoding="utf-8") as handle:
        for entry in translations.values():
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    cache["updated_at"] = _utc_now()


def _make_cache_key(source_id: str, source_language: str, target_language: str) -> str:
    return f"{source_id}||{source_language}||{target_language}"


def get_cached_translation(
    cache: dict[str, Any],
    source_id: str,
    source_language: str,
    target_language: str,
) -> str | None:
    cache_key = _make_cache_key(source_id, source_language, target_language)
    entry = cache.get("translations", {}).get(cache_key)
    if entry:
        return entry.get("text")
    return None


def set_cached_translation(
    cache: dict[str, Any],
    source_id: str,
    source_language: str,
    target_language: str,
    translated_text: str,
    model: str | None = None,
    original_text: str | None = None,
    *,
    append_path: Path | None = None,
    persist: bool = True,
) -> None:
    """Store a translation in memory and optionally append one JSONL line to disk."""
    config = get_config()
    used_model = model or config.llm_translation_model
    translations = cache.setdefault("translations", {})
    cache_key = _make_cache_key(source_id, source_language, target_language)
    entry: dict[str, Any] = {
        "cache_key": cache_key,
        "source_id": source_id,
        "source_language": source_language,
        "target_language": target_language,
        "text": translated_text,
        "model": used_model,
        "translated_at": _utc_now(),
    }
    if original_text:
        entry["original_text"] = original_text

    translations[cache_key] = entry
    cache["updated_at"] = _utc_now()

    if persist:
        target_path = append_path or get_translation_cache_path()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with _cache_lock, target_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    api_key: str,
    model: str | None = None,
    thinking_level: str | None = None,
) -> str:
    """Translate text between languages using the configured Gemini model."""
    if not text or not text.strip():
        return text

    config = get_config()
    chosen_model = model or config.llm_translation_model
    chosen_thinking = thinking_level or config.llm_translation_thinking_level

    system_prompt = (
        f"You are a technical translator specializing in patent documents. "
        f"Translate the following text from {source_language} to {target_language}. "
        f"Preserve technical terms, acronyms, chemical formulas, and numbers. "
        f"Maintain the original meaning and technical precision. "
        f"Provide only the translated text without any explanation or commentary."
    )

    response = generate_content(
        api_key=api_key,
        model=chosen_model,
        contents=text,
        system_instruction=system_prompt,
        temperature=0.1,
        thinking_level=chosen_thinking,
    )
    return (response.text or "").strip()


def translate_patent_to_english(
    patent_record: dict[str, Any],
    source_language: str,
    api_key: str,
    translation_cache: dict[str, Any],
    model: str | None = None,
) -> dict[str, Any]:
    """Translate title, abstract, and claims of a patent record to English (on-demand)."""
    if source_language == "English":
        return patent_record

    abstract_list = patent_record.get("abstract")
    if isinstance(abstract_list, list):
        for abstract_entry in abstract_list:
            if isinstance(abstract_entry, dict) and abstract_entry.get("lang") == "en":
                return patent_record

    translated_record = patent_record.copy()
    patent_id = (
        patent_record.get("record_id")
        or patent_record.get("lens_id")
        or patent_record.get("epo_id")
        or "UNKNOWN"
    )

    def translate_field_if_present(field_name: str, nested_path: str, cache_suffix: str) -> str | None:
        current: Any = patent_record
        for key in nested_path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None

        if isinstance(current, list):
            if not current:
                return None
            item = current[0]
            text_to_translate = item.get("text", "") if isinstance(item, dict) else str(item)
        else:
            text_to_translate = str(current) if current else ""

        if not text_to_translate or not text_to_translate.strip():
            return None

        cached = get_cached_translation(
            translation_cache, f"{patent_id}_{cache_suffix}", source_language, "English"
        )
        if cached:
            return cached

        try:
            translated = translate_text(
                text_to_translate,
                source_language,
                "English",
                api_key,
                model=model,
            )
            set_cached_translation(
                translation_cache,
                f"{patent_id}_{cache_suffix}",
                source_language,
                "English",
                translated,
                model=model,
                original_text=text_to_translate,
            )
            return translated
        except Exception as exc:
            logger.warning("Translation failed for %s of %s: %s", cache_suffix, patent_id, exc)
            return None

    tasks = [
        ("title", "biblio.invention_title", "title", "title_en"),
        ("abstract", "abstract", "abstract", "abstract_en"),
        ("claims", "claims", "claims", "claims_en"),
    ]

    future_to_task = {
        _executor.submit(translate_field_if_present, field_name, nested_path, cache_suffix): output_key
        for field_name, nested_path, cache_suffix, output_key in tasks
    }

    for future in as_completed(future_to_task):
        output_key = future_to_task[future]
        try:
            result = future.result()
            if result:
                translated_record[output_key] = result
        except Exception as exc:
            logger.warning("Parallel translation failed for %s of %s: %s", output_key, patent_id, exc)

    return translated_record


def clear_translation_cache(path: Path | None = None) -> int:
    """Delete the translation cache file and return count of entries cleared."""
    cache_path = path or get_translation_cache_path()
    count = len(load_translation_cache(cache_path).get("translations", {}))
    with _cache_lock:
        if cache_path.exists():
            cache_path.unlink()
    return count


def get_translation_cache_stats(path: Path | None = None) -> dict[str, Any]:
    """Return entry count and file size in bytes."""
    cache_path = path or get_translation_cache_path()
    size_bytes = cache_path.stat().st_size if cache_path.exists() else 0
    count = len(load_translation_cache(cache_path).get("translations", {}))
    return {"entries": count, "size_bytes": size_bytes, "path": str(cache_path)}
