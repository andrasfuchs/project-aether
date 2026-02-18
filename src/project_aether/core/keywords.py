"""
Keyword definitions for Project Aether.
Structured by language and sentiment (positive/anomalous vs negative/false-positive).
"""

from typing import Dict, List, Set

def get_flattened_keywords(language_config: Dict[str, Dict[str, List[str]]]) -> tuple[Set[str], Set[str]]:
    """
    Flatten the structured keyword dict into two sets (positive and negative)
    for efficient lookup by the AnalystAgent.
    """
    positive_set = set()
    negative_set = set()

    for lang, categories in language_config.items():
        positive_set.update(categories.get("positive", []))
        negative_set.update(categories.get("negative", []))

    return positive_set, negative_set
