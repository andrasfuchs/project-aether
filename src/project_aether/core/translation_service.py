"""
General-purpose translation service for patent documents and abstracts.
Supports translation from any language to any language.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from project_aether.core.config import get_config


CACHE_VERSION = 1
DEFAULT_MODEL = "gemini-3-flash-preview"
MAX_PARALLEL_TRANSLATIONS = 10

# Thread-safe lock for cache operations
_cache_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.utcnow().isoformat()


def get_translation_cache_path() -> Path:
    """Get the path to the general translation cache file."""
    config = get_config()
    return config.database_path.parent / "translation_cache.json"


def _empty_translation_cache() -> Dict[str, Any]:
    """Create an empty translation cache structure."""
    return {
        "version": CACHE_VERSION,
        "translations": {},
        "updated_at": _utc_now(),
    }


def load_translation_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load the translation cache from disk."""
    cache_path = path or get_translation_cache_path()
    if not cache_path.exists():
        return _empty_translation_cache()

    try:
        with cache_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("translations", {})
        data.setdefault("version", CACHE_VERSION)
        data.setdefault("updated_at", _utc_now())
        return data
    except Exception:
        return _empty_translation_cache()


def save_translation_cache(cache: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Save the translation cache to disk."""
    cache_path = path or get_translation_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache["updated_at"] = _utc_now()
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(cache, handle, indent=2, ensure_ascii=False)


def _make_cache_key(
    source_id: str,
    source_language: str,
    target_language: str,
) -> str:
    """
    Generate a cache key for a translation.
    
    Args:
        source_id: Identifier for the source (e.g., lens_id for patents)
        source_language: Source language name
        target_language: Target language name
    
    Returns:
        A string key for caching
    """
    return f"{source_id}||{source_language}||{target_language}"


def get_cached_translation(
    cache: Dict[str, Any],
    source_id: str,
    source_language: str,
    target_language: str,
) -> Optional[str]:
    """
    Get a cached translation.
    
    Args:
        cache: The translation cache dictionary
        source_id: Identifier for the source (e.g., lens_id)
        source_language: Source language name
        target_language: Target language name
    
    Returns:
        The cached translation, or None if not available
    """
    cache_key = _make_cache_key(source_id, source_language, target_language)
    translation_entry = cache.get("translations", {}).get(cache_key)
    if translation_entry:
        return translation_entry.get("text")
    return None


def set_cached_translation(
    cache: Dict[str, Any],
    source_id: str,
    source_language: str,
    target_language: str,
    translated_text: str,
    model: str = DEFAULT_MODEL,
    original_text: Optional[str] = None,
) -> None:
    """
    Cache a translation.
    
    Args:
        cache: The translation cache dictionary
        source_id: Identifier for the source (e.g., lens_id)
        source_language: Source language name
        target_language: Target language name
        translated_text: The translated text
        model: The model used for translation
        original_text: The original text before translation (optional)
    """
    translations = cache.setdefault("translations", {})
    cache_key = _make_cache_key(source_id, source_language, target_language)
    translations[cache_key] = {
        "source_id": source_id,
        "source_language": source_language,
        "target_language": target_language,
        "text": translated_text,
        "model": model,
        "translated_at": _utc_now(),
    }
    if original_text:
        translations[cache_key]["original_text"] = original_text


def translate_text(
    text: str,
    source_language: str,
    target_language: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Translate text from one language to another using the LLM.
    
    Args:
        text: The text to translate
        source_language: Source language name (e.g., "English", "Chinese")
        target_language: Target language name (e.g., "Hungarian")
        api_key: Google API key for LLM access
        model: The LLM model to use
    
    Returns:
        The translated text
    
    Raises:
        ValueError: If text is empty
        Exception: If LLM call fails
    """
    if not text or not text.strip():
        return text
    
    system_prompt = (
        f"You are a technical translator specializing in patent documents. "
        f"Translate the following text from {source_language} to {target_language}. "
        f"Preserve technical terms, acronyms, chemical formulas, and numbers. "
        f"Maintain the original meaning and technical precision. "
        f"Provide only the translated text without any explanation or commentary."
    )
    
    # Initialize Google GenAI client
    client = genai.Client(api_key=api_key)
    
    # Generate content with Gemini using proper configuration
    response = client.models.generate_content(
        model=model,
        contents=text,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=1.0,  # Recommended default for Gemini 3 models
            thinking_config=types.ThinkingConfig(
                thinking_level=types.ThinkingLevel.LOW
            )
        )
    )
    
    return (response.text or "").strip()

def translate_patent_to_english(
    patent_record: Dict[str, Any],
    source_language: str,
    api_key: str,
    translation_cache: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> Dict[str, Any]:
    """
    Translate key fields of a patent record to English.
    
    Translates:
    - Title (from biblio.invention_title)
    - Abstract
    - Claims
    
    Returns a new patent record with English translations added.
    The original fields are preserved, and translated fields are added with '_en' suffix.
    
    Args:
        patent_record: Patent data from Lens.org API
        source_language: Source language name (e.g., "Chinese", "Japanese")
        api_key: Google API key for LLM access
        translation_cache: Translation cache dictionary (for caching translations)
        model: The LLM model to use
    
    Returns:
        Updated patent record with English translations added
    """
    import logging
    logger = logging.getLogger("TranslationService")
    
    if source_language == "English":
        # No translation needed
        return patent_record
    
    # Create a copy to avoid modifying the original
    translated_record = patent_record.copy()
    lens_id = patent_record.get("lens_id", "UNKNOWN")
    
    # Helper function to safely extract and translate text with robust caching
    def translate_field_if_present(field_name: str, nested_path: str, cache_suffix: str) -> Optional[str]:
        """
        Extract a field from the patent record and translate it.
        Uses translation cache to avoid redundant API calls.
        
        Args:
            field_name: Name of the field (for logging)
            nested_path: Dot-separated path to extract (e.g., "biblio.invention_title")
            cache_suffix: Suffix for cache key (e.g., "title", "abstract", "claims")
        
        Returns:
            Translated text or None if field not present
        """
        # Extract the field using nested path
        keys = nested_path.split('.')
        current = patent_record
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
                if current is None:
                    return None
            else:
                return None
        
        if current is None:
            return None
        
        # Handle list fields (take first element if available)
        if isinstance(current, list):
            if len(current) == 0:
                return None
            item = current[0]
            if isinstance(item, dict):
                text_to_translate = item.get("text", "")
            else:
                text_to_translate = str(item)
        else:
            text_to_translate = str(current) if current else ""
        
        if not text_to_translate or not text_to_translate.strip():
            return None
        
        # Store original text for cache
        original_text = text_to_translate
        
        # --- CACHE CHECK: Look up translation in cache ---
        cache_key = _make_cache_key(f"{lens_id}_{cache_suffix}", source_language, "English")
        cached = translation_cache.get("translations", {}).get(cache_key, {}).get("text")
        if cached:
            return cached
        
        # --- CACHE MISS: Translate and cache ---
        try:
            text_preview = original_text[:20].replace('\n', ' ')
            logger.info(f"⟳ Translating {cache_suffix} for {lens_id}: '{text_preview}...' ({source_language} → English)")
            translated = translate_text(
                text_to_translate,
                source_language,
                "English",
                api_key,
                model
            )
            
            # Save translation to cache for future use (with original text)
            # Use lock to ensure thread-safe cache updates
            with _cache_lock:
                set_cached_translation(
                    translation_cache,
                    f"{lens_id}_{cache_suffix}",
                    source_language,
                    "English",
                    translated,
                    model,
                    original_text
                )
                # Save cache to disk immediately after successful translation
                try:
                    save_translation_cache(translation_cache)
                    logger.info(f"✓ Translation complete for {cache_suffix} of {lens_id}: '{text_preview}...'")
                except Exception as save_error:
                    logger.warning(f"Failed to save cache for {cache_suffix} of {lens_id}: {save_error}")
            return translated
        except Exception as e:
            text_preview = original_text[:20].replace('\n', ' ')
            logger.warning(f"✗ Translation failed for {cache_suffix} of {lens_id}: '{text_preview}...' - {e}")
            return None
    
    # Define translation tasks
    translation_tasks = [
        ("title", "biblio.invention_title", "title", "title_en"),
        ("abstract", "abstract", "abstract", "abstract_en"),
        ("claims", "claims", "claims", "claims_en"),
    ]
    
    # Execute translations in parallel
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_TRANSLATIONS) as executor:
        # Submit all translation tasks
        future_to_task = {
            executor.submit(translate_field_if_present, field_name, nested_path, cache_suffix): (field_name, output_key)
            for field_name, nested_path, cache_suffix, output_key in translation_tasks
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_task):
            field_name, output_key = future_to_task[future]
            try:
                result = future.result()
                if result:
                    translated_record[output_key] = result
                    logger.debug(f"Added {output_key} for {lens_id}")
            except Exception as e:
                logger.warning(f"✗ Parallel translation failed for {field_name} of {lens_id}: {e}")
    
    return translated_record