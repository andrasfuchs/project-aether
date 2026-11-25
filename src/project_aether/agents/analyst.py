"""
Analyst Agent for Project Aether.
Performs forensic legal-status analysis, native-multilingual LLM scoring,
and intelligence triage of patent records.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.llm import QuotaExhaustedError, generate_content
from project_aether.core.llm_scoring import (
    DEFAULT_SCORING_MODEL,
    DEFAULT_SCORING_SYSTEM_PROMPT,
    DEFAULT_SCORING_THINKING_LEVEL,
    MAX_CONCURRENT_SCORING,
    apply_prompt_placeholders,
)
from project_aether.core.scoring_cache import (
    get_cached_score,
    load_scoring_cache,
    set_cached_score,
)
from project_aether.tools.inpadoc import (
    StatusAnalysis,
    StatusSeverity,
    analyze_legal_status,
)

logger = logging.getLogger("AnalystAgent")

_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SCORING)
_scoring_cache_lock = threading.Lock()


class PatentScoringResponse(BaseModel):
    score: float = Field(ge=0, le=100)
    title_en: str = ""
    domain_category: str = ""
    tags: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    rationale: str = ""


def _safe_get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    keys = path.split(".")
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    return current if current is not None else default


def _extract_party_names(parties_data: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(parties_data, list):
        return names
    for party in parties_data:
        if not isinstance(party, dict):
            continue
        name = None
        extracted = party.get("extracted_name")
        if isinstance(extracted, dict):
            name = extracted.get("value")
        if not name:
            name = party.get("name") or party.get("full_name")
        if name and isinstance(name, str):
            names.append(name.strip())
    return names


@dataclass
class PatentAssessment:
    """Complete assessment of a patent's intelligence value."""

    record_id: str
    lens_id: str | None
    epo_id: str | None
    provider_name: str
    provider_record_url: str | None
    jurisdiction: str
    doc_number: str
    title: str
    inventors: list[str]

    # Legal analysis
    status_analysis: StatusAnalysis

    # Semantic analysis
    relevance_score: float
    is_anomalous: bool
    classification_tags: list[str]
    llm_tags: list[str]
    llm_features: list[str]

    # Summary
    intelligence_value: str  # "HIGH", "MEDIUM", "LOW"
    summary: str

    # Extended metadata
    title_en: str | None = None
    domain_category: str = ""
    rationale: str = ""
    legal_history_url: str | None = None
    date_published: str | None = None
    applicants: list[str] = field(default_factory=list)
    all_classifications: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "lens_id": self.lens_id,
            "epo_id": self.epo_id,
            "provider_name": self.provider_name,
            "provider_record_url": self.provider_record_url,
            "legal_history_url": self.legal_history_url,
            "jurisdiction": self.jurisdiction,
            "doc_number": self.doc_number,
            "date_published": self.date_published,
            "title": self.title,
            "title_en": self.title_en,
            "inventors": self.inventors,
            "applicants": self.applicants,
            "status_analysis": self.status_analysis.to_dict(),
            "relevance_score": self.relevance_score,
            "is_anomalous": self.is_anomalous,
            "classification_tags": self.classification_tags,
            "all_classifications": self.all_classifications,
            "llm_tags": self.llm_tags,
            "llm_features": self.llm_features,
            "domain_category": self.domain_category,
            "rationale": self.rationale,
            "intelligence_value": self.intelligence_value,
            "summary": self.summary,
        }


class AnalystAgent:
    """
    The Domain Expert Agent.
    Performs forensic analysis and native-multilingual LLM scoring of patent data.
    """

    def __init__(
        self,
        keyword_config: dict[str, Any] | None = None,
        scoring_system_prompt: str | None = None,
        scoring_model: str | None = None,
        scoring_thinking_level: str | None = None,
        relevance_threshold: float = 40.0,
        high_threshold: float = 70.0,
        calibration_examples: str = "",
    ):
        self.logger = logger
        self.config = get_config()
        self.scoring_system_prompt = scoring_system_prompt or DEFAULT_SCORING_SYSTEM_PROMPT
        self.scoring_model = scoring_model or self.config.llm_scoring_model or DEFAULT_SCORING_MODEL
        self.scoring_thinking_level = (
            scoring_thinking_level
            or self.config.llm_scoring_thinking_level
            or DEFAULT_SCORING_THINKING_LEVEL
        )
        self.relevance_threshold = float(relevance_threshold)
        self.high_threshold = max(float(high_threshold), self.relevance_threshold)
        self.calibration_examples = calibration_examples or ""
        self.scoring_cache = load_scoring_cache()

        active_keyword_config = keyword_config or {"English": {"positive": [], "negative": []}}
        self.positive_groups, self.false_positive_keywords = get_active_english_keywords(
            active_keyword_config
        )
        self.anomalous_keywords = sorted(
            {term for group in self.positive_groups for term in group if term}
        )

        # Precompute deterministic system prompt once for batch prefix-cache efficiency
        self._resolved_system_prompt = apply_prompt_placeholders(
            self.scoring_system_prompt,
            self.positive_groups,
            self.false_positive_keywords,
            calibration_examples=self.calibration_examples,
        )

        self.high_value_classifications = {
            "G21B 3/00",  # Low temperature nuclear fusion
            "H01J 37/00",  # Discharge tubes
            "H05H 1/00",  # Plasma technique
            "C25B 1/00",  # Electrolytic production
        }

    def analyze_patent(
        self,
        patent_record: dict[str, Any],
        progress_callback: Callable[..., Any] | None = None,
    ) -> PatentAssessment:
        _ = progress_callback
        record_id = (
            patent_record.get("record_id")
            or patent_record.get("lens_id")
            or patent_record.get("epo_id")
            or "UNKNOWN"
        )
        lens_id = patent_record.get("lens_id")
        epo_id = patent_record.get("epo_id")
        provider_name = patent_record.get("provider_name", "unknown")
        provider_record_url = patent_record.get("provider_record_url")
        legal_history_url = patent_record.get("legal_history_url")
        jurisdiction = patent_record.get("jurisdiction", "UNKNOWN")
        doc_number = patent_record.get("doc_number", "UNKNOWN")
        date_published = patent_record.get("date_published")

        title_data = _safe_get_nested(patent_record, "biblio.invention_title")
        if isinstance(title_data, list) and title_data:
            first = title_data[0]
            title = first.get("text", "Untitled") if isinstance(first, dict) else str(first)
        elif isinstance(title_data, dict):
            title = title_data.get("text", "Untitled")
        elif isinstance(title_data, str):
            title = title_data
        else:
            title = "Untitled"

        inventors = _extract_party_names(
            _safe_get_nested(patent_record, "biblio.parties.inventors", [])
        )
        applicants = _extract_party_names(
            _safe_get_nested(patent_record, "biblio.parties.applicants", [])
        )

        status_analysis = analyze_legal_status(patent_record)

        # Prefer English abstract if already available on record, otherwise native abstract
        abstract_data = patent_record.get("abstract_en") or patent_record.get("abstract", "")
        if isinstance(abstract_data, list) and abstract_data:
            en_item = next(
                (a for a in abstract_data if isinstance(a, dict) and a.get("lang") == "en"),
                None,
            )
            chosen = en_item or abstract_data[0]
            abstract = chosen.get("text", "") if isinstance(chosen, dict) else str(chosen)
        else:
            abstract = str(abstract_data) if abstract_data else ""

        claims_data = patent_record.get("claims_en") or patent_record.get("claims", "")
        if isinstance(claims_data, list) and claims_data:
            first_claim = claims_data[0]
            claims = (
                first_claim.get("text", "")
                if isinstance(first_claim, dict)
                else str(first_claim)
            )
        else:
            claims = str(claims_data) if claims_data else ""

        classification_tags, all_classifications = self._extract_classification_tags(patent_record)

        llm_result = self._score_with_llm(
            record_id=record_id,
            title=title,
            abstract=abstract,
            jurisdiction=jurisdiction,
            classifications=all_classifications,
            status_summary=status_analysis.interpretation,
        )
        relevance_score = llm_result["score"]
        title_en = llm_result.get("title_en") or patent_record.get("title_en") or None
        if title_en and title_en.strip().lower() == title.strip().lower():
            title_en = None
        domain_category = llm_result.get("domain_category", "")
        rationale = llm_result.get("rationale", "")
        llm_tags = llm_result["tags"]
        llm_features = llm_result["features"]

        searchable_text = f"{title_en or title} {abstract} {claims}".lower()
        is_anomalous = self._is_anomalous_content(searchable_text)

        intelligence_value = self._determine_intelligence_value(
            status_analysis,
            relevance_score,
            classification_tags,
        )

        summary = self._generate_summary(
            status_analysis,
            relevance_score,
            is_anomalous,
            classification_tags,
        )

        return PatentAssessment(
            record_id=record_id,
            lens_id=lens_id,
            epo_id=epo_id,
            provider_name=provider_name,
            provider_record_url=provider_record_url,
            legal_history_url=legal_history_url,
            jurisdiction=jurisdiction,
            doc_number=doc_number,
            date_published=date_published,
            title=title,
            title_en=title_en,
            inventors=inventors,
            applicants=applicants,
            status_analysis=status_analysis,
            relevance_score=relevance_score,
            is_anomalous=is_anomalous,
            classification_tags=classification_tags,
            all_classifications=all_classifications,
            llm_tags=llm_tags,
            llm_features=llm_features,
            domain_category=domain_category,
            rationale=rationale,
            intelligence_value=intelligence_value,
            summary=summary,
        )

    def _calculate_relevance_score(self, text: str) -> float:
        """Fallback keyword-based relevance score when LLM key is absent."""
        score = 0.0
        anomalous_hits = sum(1 for kw in self.anomalous_keywords if kw.lower() in text)
        score += anomalous_hits * 15
        false_positive_hits = sum(
            1 for kw in self.false_positive_keywords if kw.lower() in text
        )
        score -= false_positive_hits * 20
        if "hydrogen" in text or "deuterium" in text:
            score += 10
        if "plasma" in text or "discharge" in text:
            score += 10
        return max(0.0, min(100.0, score))

    def _score_with_llm(
        self,
        *,
        record_id: str,
        title: str,
        abstract: str,
        jurisdiction: str,
        classifications: list[str],
        status_summary: str,
    ) -> dict[str, Any]:
        with _scoring_cache_lock:
            cached = get_cached_score(
                self.scoring_cache,
                record_id,
                title,
                abstract,
                self._resolved_system_prompt,
                self.scoring_model,
                self.scoring_thinking_level,
            )
        if cached:
            cached_score = float(cached.get("score", 0.0))
            logger.debug(
                "Using cached score for %s (%s): %.2f",
                record_id,
                jurisdiction,
                cached_score,
            )
            return {
                "score": cached_score,
                "title_en": cached.get("title_en") or "",
                "domain_category": cached.get("domain_category") or "",
                "tags": cached.get("tags", []) or [],
                "features": cached.get("features", []) or [],
                "rationale": cached.get("rationale") or "",
            }

        if not self.config.google_api_key:
            logger.warning("LLM scoring skipped: GEMINI_API_KEY not configured")
            return {
                "score": 0.0,
                "title_en": "",
                "domain_category": "",
                "tags": [],
                "features": [],
                "rationale": "LLM scoring skipped (no GEMINI_API_KEY).",
            }

        ipc_text = ", ".join(classifications[:10]) if classifications else "None"
        user_prompt = (
            f"Jurisdiction: {jurisdiction}\n"
            f"IPC/CPC: {ipc_text}\n"
            f"Legal Status: {status_summary}\n\n"
            f"Title:\n{title}\n\n"
            f"Abstract:\n{abstract}"
        )

        response = generate_content(
            api_key=self.config.google_api_key,
            model=self.scoring_model,
            contents=user_prompt,
            system_instruction=self._resolved_system_prompt,
            temperature=0.1,
            thinking_level=self.scoring_thinking_level,
            response_schema=PatentScoringResponse,
            response_mime_type="application/json",
        )

        parsed = self._parse_llm_json(response.text or "{}")
        score = max(0.0, min(100.0, float(parsed.get("score", 0.0))))
        title_en = str(parsed.get("title_en") or "").strip()
        domain_category = str(parsed.get("domain_category") or "").strip()
        rationale = str(parsed.get("rationale") or "").strip()

        raw_tags = parsed.get("tags") or []
        if not isinstance(raw_tags, list):
            raw_tags = [str(raw_tags)]
        tags = [str(tag).strip() for tag in raw_tags if str(tag).strip()]

        raw_features = parsed.get("features") or []
        if not isinstance(raw_features, list):
            raw_features = [str(raw_features)]
        features = [str(f).strip() for f in raw_features if str(f).strip()]

        logger.debug("Determined LLM score for %s (%s): %.2f", record_id, jurisdiction, score)

        with _scoring_cache_lock:
            set_cached_score(
                self.scoring_cache,
                record_id=record_id,
                title=title,
                abstract=abstract,
                system_message=self._resolved_system_prompt,
                model=self.scoring_model,
                thinking_level=self.scoring_thinking_level,
                score=score,
                title_en=title_en,
                domain_category=domain_category,
                tags=tags,
                features=features,
                rationale=rationale,
                persist=True,
            )

        return {
            "score": score,
            "title_en": title_en,
            "domain_category": domain_category,
            "tags": tags,
            "features": features,
            "rationale": rationale,
        }

    def _parse_llm_json(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {}

    def _is_anomalous_content(self, text: str) -> bool:
        for keyword in self.anomalous_keywords:
            if keyword.lower() in text:
                return True
        return bool(("over-unity" in text or "excess" in text) and ("energy" in text or "heat" in text))

    def _extract_classification_tags(
        self, patent_record: dict[str, Any]
    ) -> tuple[list[str], list[str]]:
        high_value_tags: list[str] = []
        all_symbols: list[str] = []

        for field_path in ("biblio.classifications_ipcr", "biblio.classifications_cpc"):
            items = _safe_get_nested(patent_record, field_path, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict):
                    symbol = str(item.get("symbol") or "").strip()
                    if symbol:
                        all_symbols.append(symbol)
                        if any(hv in symbol for hv in self.high_value_classifications):
                            high_value_tags.append(symbol)

        return list(dict.fromkeys(high_value_tags)), list(dict.fromkeys(all_symbols))

    def _determine_intelligence_value(
        self,
        status_analysis: StatusAnalysis,
        relevance_score: float,
        classification_tags: list[str],
    ) -> str:
        """
        Determine priority tier driven primarily by relevance score,
        boosted when substantive refusal or high-value IPC/CPC codes are present.
        """
        if relevance_score >= self.high_threshold:
            return "HIGH"

        if relevance_score >= self.relevance_threshold and (
            status_analysis.severity == StatusSeverity.HIGH or bool(classification_tags)
        ):
            return "HIGH"

        if relevance_score >= self.relevance_threshold:
            return "MEDIUM"

        if status_analysis.severity == StatusSeverity.HIGH and relevance_score >= 25.0:
            return "MEDIUM"

        return "LOW"

    def _generate_summary(
        self,
        status_analysis: StatusAnalysis,
        relevance_score: float,
        is_anomalous: bool,
        classification_tags: list[str],
    ) -> str:
        parts = []
        if status_analysis.is_refused:
            parts.append(f"🚨 Substantively refused: {status_analysis.refusal_reason}")
        elif status_analysis.is_withdrawn:
            parts.append("⚠️ Withdrawn by applicant")
        else:
            parts.append(f"ℹ️ {status_analysis.interpretation}")

        if relevance_score >= self.high_threshold:
            parts.append(f"📊 High relevance score: {relevance_score:.0f}/100")
        elif relevance_score >= self.relevance_threshold:
            parts.append(f"📊 Moderate relevance: {relevance_score:.0f}/100")
        else:
            parts.append(f"📊 Low relevance: {relevance_score:.0f}/100")

        if is_anomalous:
            parts.append("⚡ Contains anomalous phenomena terminology")
        if classification_tags:
            parts.append(f"🏷️ High-value classifications: {', '.join(classification_tags)}")
        return " | ".join(parts)

    def analyze_batch(
        self,
        patent_records: list[dict[str, Any]],
        progress_callback: Callable[[int, int, str, PatentAssessment | None], None] | None = None,
    ) -> list[PatentAssessment]:
        assessments_by_index: list[PatentAssessment | None] = [None] * len(patent_records)
        completed_count = 0

        future_to_index = {
            _executor.submit(self.analyze_patent, record): index
            for index, record in enumerate(patent_records)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            try:
                assessment = future.result()
                assessments_by_index[index] = assessment
                completed_count += 1

                if progress_callback:
                    msg = f"Analyzed {completed_count}/{len(patent_records)} patents"
                    progress_callback(completed_count, len(patent_records), msg, assessment)

                if assessment.intelligence_value == "HIGH":
                    logger.info(
                        "🎯 HIGH VALUE TARGET: %s (%s) - %s",
                        assessment.record_id,
                        assessment.jurisdiction,
                        assessment.summary,
                    )
            except QuotaExhaustedError:
                for pending in future_to_index:
                    pending.cancel()
                raise
            except Exception as exc:
                logger.error("Failed to analyze patent: %s", exc)
                completed_count += 1
                if progress_callback:
                    msg = f"Analyzed {completed_count}/{len(patent_records)} patents"
                    progress_callback(completed_count, len(patent_records), msg, None)

        results = [a for a in assessments_by_index if a is not None]
        high_n = sum(1 for a in results if a.intelligence_value == "HIGH")
        med_n = sum(1 for a in results if a.intelligence_value == "MEDIUM")
        low_n = len(results) - high_n - med_n
        logger.info(
            "Batch scoring complete: %d/%d patents (HIGH=%d, MEDIUM=%d, LOW=%d)",
            len(results),
            len(patent_records),
            high_n,
            med_n,
            low_n,
        )
        return results

    def filter_high_priority(self, assessments: list[PatentAssessment]) -> list[PatentAssessment]:
        return [a for a in assessments if a.intelligence_value == "HIGH"]
