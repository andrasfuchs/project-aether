"""
General-purpose translation service for patent documents and abstracts.
Supports translation from any language to any language.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from project_aether.core.config import get_config


CACHE_VERSION = 1
DEFAULT_MODEL = "gemini-3-pro-preview"


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
    
    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.2,
        model_kwargs={
            "thinking_config": {
                "thinking_budget": 1024
            }
        }
    )
    
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=text),
    ])
    
    # Handle response.content which might be a string or other type
    content = response.content
    if isinstance(content, list):
        # If content is a list of message parts, extract text from each part
        text_parts = []
        for part in content:
            if isinstance(part, dict) and 'text' in part:
                text_parts.append(part['text'])
            elif isinstance(part, str):
                text_parts.append(part)
            else:
                text_parts.append(str(part))
        content = " ".join(text_parts)
    elif not isinstance(content, str):
        content = str(content)
    
    return content.strip()

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
        
        # --- CACHE CHECK: Look up translation in cache ---
        cache_key = _make_cache_key(f"{lens_id}_{cache_suffix}", source_language, "English")
        cached = translation_cache.get("translations", {}).get(cache_key, {}).get("text")
        if cached:
            logger.info(f"✓ Cache HIT: {cache_suffix} for {lens_id} ({source_language} → English)")
            return cached
        
        # --- CACHE MISS: Translate and cache ---
        try:
            logger.info(f"⟳ Cache MISS: Translating {cache_suffix} for {lens_id} ({source_language} → English)")
            translated = translate_text(
                text_to_translate,
                source_language,
                "English",
                api_key,
                model
            )
            
            # Save translation to cache for future use
            set_cached_translation(
                translation_cache,
                f"{lens_id}_{cache_suffix}",
                source_language,
                "English",
                translated,
                model
            )
            logger.debug(f"✓ Cached translation for {cache_suffix} of {lens_id}")
            return translated
        except Exception as e:
            logger.warning(f"✗ Translation failed for {cache_suffix} of {lens_id}: {e}")
            return None
    
    # 1. Translate Title
    title_en = translate_field_if_present("title", "biblio.invention_title", "title")
    if title_en:
        translated_record["title_en"] = title_en
        logger.debug(f"Added title_en for {lens_id}")
    
    # 2. Translate Abstract
    abstract_en = translate_field_if_present("abstract", "abstract", "abstract")
    if abstract_en:
        translated_record["abstract_en"] = abstract_en
        logger.debug(f"Added abstract_en for {lens_id}")
    
    # 3. Translate Claims
    claims_en = translate_field_if_present("claims", "claims", "claims")
    if claims_en:
        translated_record["claims_en"] = claims_en
        logger.debug(f"Added claims_en for {lens_id}")
    
    return translated_record