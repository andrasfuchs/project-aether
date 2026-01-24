"""
Keyword definitions for Project Aether.
Structured by language and sentiment (positive/anomalous vs negative/false-positive).
"""

from typing import Dict, List, Set

# Default keyword dictionary
DEFAULT_KEYWORDS = {
    "English": {
        "positive": [
            "anomalous heat", "excess energy", "over-unity", "cold fusion",
            "LENR", "LANR", "transmutation", "plasma vortex", "plasmoid",
            "excess enthalpy", "non-chemical heat", "lattice assisted",
            "condensed matter nuclear", "Rydberg matter"
        ],
        "negative": [
            "spark plug", "ignition system", "internal combustion",
            "automotive", "engine", "combustion chamber",
            "fuel injection", "cylinder head", "piston"
        ]
    },
    "Russian": {
        "positive": [
            "аномальное тепловыделение", "избыточное энерговыделение",
            "холодный синтез", "холодный ядерный синтез",
            "трансмутация элементов", "плазменный вихрь",
            "тлеющий разряд", "электролизная плазма"
        ],
        "negative": [
            "свеча зажигания", "система зажигания", "внутреннего сгорания",
            "автомобильный", "двигатель", "камера сгорания"
        ]
    },
    # Placeholders for other languages
    "Polish": {
        "positive": [],
        "negative": []
    },
    "Romanian": {
        "positive": [],
        "negative": []
    }
}

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
