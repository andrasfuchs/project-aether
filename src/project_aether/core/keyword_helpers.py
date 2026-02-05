from typing import List, Tuple

from project_aether.core.keyword_translation import normalize_terms


def get_active_english_keywords(kw_config: dict) -> tuple[List[str], List[str]]:
    english = kw_config.get("English", {})
    include_terms = normalize_terms(english.get("positive", []))
    exclude_terms = normalize_terms(english.get("negative", []))
    return include_terms, exclude_terms


def translation_context() -> str:
    return (
        "The keywords are for patent searches related to anomalous heat, "
        "low energy nuclear reactions (LENR), plasma discharge phenomena, "
        "transmutation, and excess energy claims. The terms appear in patent "
        "titles and abstracts and should be translated into technical, "
        "domain-appropriate language."
    )
