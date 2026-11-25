"""
Defaults and helpers for LLM-based patent scoring.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_SCORING_MODEL = "gemini-4-hydrogen"
DEFAULT_SCORING_THINKING_LEVEL = "low"
MAX_CONCURRENT_SCORING = 15

DEFAULT_SCORING_SYSTEM_PROMPT = (
    "You are a patent relevance scoring model for anomalous energy research "
    "(sparks/discharges in hydrogen or water vapor, plasma physics, anomalous heat, LENR, transmutation).\n"
    "Score the patent from 0 to 100 based on the title, abstract, IPC/CPC classifications, and legal status provided.\n"
    "Use the following weighting guidance:\n"
    "- Strong evidence of anomalous heat, LENR, or excess energy: +35\n"
    "- Experimental apparatus or repeatable test setup in H2/D2/water vapor plasma: +20\n"
    "- Plasma discharge, transmutation, or low-temperature fusion: +15\n"
    "- Vague or speculative claims without physical mechanism/data: -15\n"
    "- Conventional combustion, spark plugs, EDM/wire-bonding/machining, standard electrolysis, or unrelated tech: -35\n"
    "Incorporate the active keyword groups and exclude terms into your judgment:\n"
    "Positive keyword groups (AND between groups, OR within a group): {positive_keywords}\n"
    "Negative / exclude terms: {negative_keywords}\n"
    "{calibration_examples}"
    "Return JSON only matching the schema: "
    "score (0-100), title_en (concise English translation of the title, or original if already English), "
    "domain_category (short label like 'Anomalous Plasma/LENR', 'Automotive/ICE', 'EDM/Machining', 'Standard Electrolysis', 'Other'), "
    "tags (array of short terms), features (array of short notable technical phrases), "
    "and rationale (1-2 concise sentences explaining why this score was assigned)."
)


def format_keyword_groups(positive_keywords: Iterable[str | Iterable[str]]) -> str:
    """Format grouped or flat positive keywords deterministically."""
    formatted_groups: list[str] = []
    for item in positive_keywords:
        if isinstance(item, (list, tuple, set)):
            terms = sorted({str(t).strip() for t in item if str(t).strip()})
            if terms:
                formatted_groups.append("(" + " OR ".join(terms) + ")")
        else:
            term = str(item).strip()
            if term:
                formatted_groups.append(term)
    return " AND ".join(sorted(formatted_groups)) or "None"


def apply_prompt_placeholders(
    prompt: str,
    positive_keywords: Iterable[str | Iterable[str]],
    negative_keywords: Iterable[str],
    calibration_examples: str = "",
) -> str:
    positive_text = format_keyword_groups(positive_keywords)
    negative_text = ", ".join(sorted({str(t).strip() for t in negative_keywords if str(t).strip()})) or "None"
    return (
        prompt
        .replace("{positive_keywords}", positive_text)
        .replace("{negative_keywords}", negative_text)
        .replace("{calibration_examples}", calibration_examples)
    )
