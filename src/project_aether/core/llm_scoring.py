"""
Defaults and helpers for LLM-based patent scoring.
"""

from __future__ import annotations

from typing import Iterable


DEFAULT_SCORING_MODEL = "gemini-3-pro-preview"

DEFAULT_SCORING_SYSTEM_PROMPT = (
    "You are a patent relevance scoring model for anomalous energy research. "
    "Score the patent from 0 to 100 based on the title and abstract provided. "
    "Use the following weighting guidance:\n"
    "- Strong evidence of anomalous heat, LENR, or excess energy: +35\n"
    "- Experimental apparatus or repeatable test setup: +20\n"
    "- Plasma discharge, transmutation, or low-temperature fusion: +15\n"
    "- Vague or speculative claims without data: -15\n"
    "- Conventional combustion, standard electrolysis, or unrelated tech: -35\n"
    "Incorporate the positive and negative keyword lists into the score. "
    "Positive keywords should increase relevance, negative keywords should decrease it. "
    "Positive keywords: {positive_keywords}\n"
    "Negative keywords: {negative_keywords}\n"
    "Return JSON only with keys: score (number 0-100), tags (array of short terms), "
    "and features (array of short notable feature phrases)."
)


def apply_prompt_placeholders(
    prompt: str,
    positive_keywords: Iterable[str],
    negative_keywords: Iterable[str],
) -> str:
    positive_text = ", ".join(positive_keywords) or "None"
    negative_text = ", ".join(negative_keywords) or "None"
    return (
        prompt
        .replace("{positive_keywords}", positive_text)
        .replace("{negative_keywords}", negative_text)
    )
