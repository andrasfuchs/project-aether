"""
Keyword definitions for Project Aether.
Structured by language and sentiment (positive/anomalous vs negative/false-positive).
"""

from typing import Any


def get_flattened_keywords(language_config: dict[str, dict[str, list[Any]]]) -> tuple[set[str], set[str]]:
    """
    Flatten the structured keyword dict into two sets (positive and negative)
    for efficient lookup by the AnalystAgent. Positive lists might be a list of lists of synonyms.
    """
    positive_set = set()
    negative_set = set()

    for categories in language_config.values():
        for item in categories.get("positive", []):
            if isinstance(item, list):
                positive_set.update(item)
            else:
                positive_set.add(item)
        negative_set.update(categories.get("negative", []))

    return positive_set, negative_set
