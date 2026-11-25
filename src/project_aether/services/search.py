"""
Pure-Python patent search & analysis orchestration service.
Decoupled from Streamlit so it can be tested directly and reused for future
scheduled reports.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from project_aether.agents.analyst import AnalystAgent, PatentAssessment
from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import (
    get_active_english_keywords,
    translation_context,
)
from project_aether.core.keyword_translation import (
    ensure_keyword_set,
    get_cached_translation,
    keyword_set_id,
    load_keyword_cache,
    save_keyword_cache,
    set_cached_translation,
    translate_keywords_with_llm,
)
from project_aether.core.llm_scoring import (
    DEFAULT_SCORING_MODEL,
    DEFAULT_SCORING_SYSTEM_PROMPT,
    DEFAULT_SCORING_THINKING_LEVEL,
)
from project_aether.core.reviews import build_calibration_prompt_block
from project_aether.core.search_cache import (
    clean_expired_entries,
    get_cached_search_results,
    load_search_cache,
    set_cached_search_results,
)
from project_aether.tools.epo_api import EPOConnector
from project_aether.tools.lens_api import LensConnector
from project_aether.utils.artifacts import ArtifactGenerator, DashboardArtifact

logger = logging.getLogger("ProjectAether")

PATENTS_PER_LANGUAGE = 1000


@dataclass
class SearchProgressEvent:
    status_text: str
    progress_percent: int
    total_scanned: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


@dataclass
class SearchRunResult:
    assessments: list[PatentAssessment] = field(default_factory=list)
    raw_results: list[dict[str, Any]] = field(default_factory=list)
    dashboard: DashboardArtifact | None = None
    search_diagnostics: list[dict[str, Any]] = field(default_factory=list)
    keyword_cache: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _emit_progress(
    callback: Callable[[SearchProgressEvent], None] | None,
    *,
    status_text: str,
    progress_percent: int,
    total_scanned: int = 0,
    high_count: int = 0,
    medium_count: int = 0,
    low_count: int = 0,
) -> None:
    if callback is None:
        return
    callback(
        SearchProgressEvent(
            status_text=status_text,
            progress_percent=max(0, min(100, int(progress_percent))),
            total_scanned=total_scanned,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
        )
    )


def execute_patent_search(
    *,
    language_codes: list[str],
    language_names: list[str],
    keyword_config: dict[str, Any],
    keyword_cache: dict[str, Any] | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    jurisdiction: str | None = None,
    patent_status_filter: list[str] | None = None,
    patents_per_language: int = PATENTS_PER_LANGUAGE,
    scoring_model: str | None = None,
    scoring_thinking_level: str | None = None,
    scoring_system_prompt: str | None = None,
    keyword_model: str | None = None,
    keyword_thinking_level: str | None = None,
    relevance_threshold: float = 40.0,
    high_threshold: float = 70.0,
    use_calibration_examples: bool = True,
    force_refresh_search: bool = False,
    progress_callback: Callable[[SearchProgressEvent], None] | None = None,
) -> SearchRunResult:
    """
    Execute multilingual patent search, deduplication, and native-multilingual
    LLM scoring/analysis without UI coupling.
    """
    result_bundle = SearchRunResult()
    if end_date is None:
        end_date = datetime.now()

    _emit_progress(progress_callback, status_text="Initializing", progress_percent=5)

    config = get_config()
    selected_provider = config.normalized_patent_provider
    if selected_provider == "lens":
        primary_connector: Any = LensConnector()
        fallback_provider = "epo"
        fallback_connector: Any = EPOConnector()
    else:
        primary_connector = EPOConnector()
        fallback_provider = "lens"
        fallback_connector = LensConnector()

    if not keyword_config:
        result_bundle.errors.append(
            "No active keyword set found. Set Include/Exclude terms in the sidebar before searching."
        )
        return result_bundle

    cache = keyword_cache if keyword_cache is not None else load_keyword_cache()
    include_terms, exclude_terms = get_active_english_keywords(keyword_config)
    if not include_terms:
        result_bundle.errors.append(
            "At least one include keyword is required. Update the active keyword set in the sidebar."
        )
        return result_bundle

    ensure_keyword_set(cache, include_terms, exclude_terms)
    save_keyword_cache(cache)
    result_bundle.keyword_cache = cache

    calibration_block = build_calibration_prompt_block() if use_calibration_examples else ""
    chosen_scoring_model = scoring_model or config.llm_scoring_model or DEFAULT_SCORING_MODEL
    chosen_scoring_thinking = (
        scoring_thinking_level
        or config.llm_scoring_thinking_level
        or DEFAULT_SCORING_THINKING_LEVEL
    )
    chosen_prompt = scoring_system_prompt or DEFAULT_SCORING_SYSTEM_PROMPT

    analyst = AnalystAgent(
        keyword_config=keyword_config,
        scoring_system_prompt=chosen_prompt,
        scoring_model=chosen_scoring_model,
        scoring_thinking_level=chosen_scoring_thinking,
        relevance_threshold=relevance_threshold,
        high_threshold=high_threshold,
        calibration_examples=calibration_block,
    )
    generator = ArtifactGenerator()

    search_cache = load_search_cache()
    expired_count = clean_expired_entries(search_cache)
    if expired_count > 0:
        logger.info("Cleaned %d expired search cache entries", expired_count)

    all_results: list[dict[str, Any]] = []
    seen_record_ids: set[str] = set()
    search_diagnostics: list[dict[str, Any]] = []
    limit = None if patents_per_language >= 1000 else int(patents_per_language)
    total_langs = max(1, len(language_codes))

    for lang_idx, (language_code, language_name) in enumerate(zip(language_codes, language_names)):
        base_pct = 10 + int(lang_idx * (35 / total_langs))
        _emit_progress(
            progress_callback,
            status_text=f"Searching in {language_name} ({lang_idx + 1}/{total_langs})",
            progress_percent=base_pct,
            total_scanned=len(all_results),
        )

        final_include_terms = include_terms
        final_exclude_terms = exclude_terms

        if language_name != "English":
            set_id = keyword_set_id(include_terms, exclude_terms)
            cached_translation = get_cached_translation(cache, set_id, language_name)

            if cached_translation:
                final_include_terms = cached_translation.get("include", include_terms)
                final_exclude_terms = cached_translation.get("exclude", exclude_terms)
                _emit_progress(
                    progress_callback,
                    status_text=f"Using cached keyword translations for {language_name}",
                    progress_percent=base_pct + 2,
                    total_scanned=len(all_results),
                )
            elif config.google_api_key:
                _emit_progress(
                    progress_callback,
                    status_text=f"Translating keywords to {language_name}...",
                    progress_percent=base_pct + 2,
                    total_scanned=len(all_results),
                )
                try:
                    final_include_terms, final_exclude_terms = translate_keywords_with_llm(
                        include_terms=include_terms,
                        exclude_terms=exclude_terms,
                        target_language=language_name,
                        context=translation_context(),
                        api_key=config.google_api_key,
                        model=keyword_model or config.llm_keyword_model,
                        thinking_level=keyword_thinking_level or config.llm_keyword_thinking_level,
                    )
                    set_cached_translation(
                        cache,
                        set_id=set_id,
                        language=language_name,
                        include_terms=final_include_terms,
                        exclude_terms=final_exclude_terms,
                        source="llm",
                        model=keyword_model or config.llm_keyword_model,
                    )
                    save_keyword_cache(cache)
                    logger.info("Translated keywords to %s using LLM", language_name)
                except Exception as exc:
                    logger.warning("LLM keyword translation failed for %s: %s", language_name, exc)
            else:
                logger.warning("No translation available for %s, using English terms", language_name)

        try:
            query_start_date = start_date.strftime("%Y-%m-%d") if start_date else None
            query_end_date = end_date.strftime("%Y-%m-%d")

            cached_result = None
            if not force_refresh_search:
                cached_result = get_cached_search_results(
                    cache=search_cache,
                    provider=selected_provider,
                    jurisdiction=jurisdiction,
                    start_date=query_start_date,
                    end_date=query_end_date,
                    positive_keywords=final_include_terms,
                    negative_keywords=final_exclude_terms,
                    patent_status_filter=patent_status_filter,
                    language=language_code,
                    limit=limit,
                )

            keyword_progress = {
                "completed": 0,
                "total": max(1, len(final_include_terms)),
            }

            def _on_keyword_search_progress(
                event: dict[str, Any],
                _kw_progress: dict[str, int] = keyword_progress,
                _base_pct: int = base_pct,
                _lang_name: str = language_name,
            ) -> None:
                _kw_progress["completed"] = int(
                    event.get("completed", _kw_progress["completed"])
                )
                _kw_progress["total"] = max(
                    1, int(event.get("total", _kw_progress["total"]))
                )
                keyword = str(event.get("keyword", ""))
                message = str(event.get("message", ""))
                keyword_short = f"{keyword[:32]}..." if len(keyword) > 35 else keyword
                progress_within_lang = _kw_progress["completed"] / _kw_progress["total"]
                pct = _base_pct + int(progress_within_lang * (25 / total_langs))

                if message:
                    status_text = f"Searching {_lang_name}: {message}"
                else:
                    status_text = (
                        f"Searching {_lang_name}: keyword "
                        f"{_kw_progress['completed']}/{_kw_progress['total']}"
                    )
                    if keyword_short:
                        status_text += f" ({keyword_short})"

                _emit_progress(
                    progress_callback,
                    status_text=status_text,
                    progress_percent=pct,
                    total_scanned=len(all_results),
                )

            if cached_result is not None:
                logger.info(
                    "Using cached search results for %s (%d results)",
                    language_name,
                    len(cached_result.get("data", [])),
                )
                search_result = cached_result
                provider_used = search_result.get("provider_used", selected_provider)
                fallback_reason = search_result.get("fallback_reason")
            else:
                try:
                    search_result = asyncio.run(
                        primary_connector.search_by_jurisdiction(
                            jurisdiction=jurisdiction,
                            start_date=query_start_date,
                            end_date=query_end_date,
                            positive_keywords=final_include_terms,
                            negative_keywords=final_exclude_terms,
                            patent_status_filter=patent_status_filter,
                            language=language_code,
                            limit=limit,
                            progress_callback=_on_keyword_search_progress,
                        )
                    )
                    provider_used = selected_provider
                    fallback_reason = None
                except Exception as primary_exc:
                    logger.warning(
                        "Primary provider (%s) failed for %s: %s. Trying fallback provider.",
                        selected_provider,
                        language_name,
                        primary_exc,
                    )
                    try:
                        search_result = asyncio.run(
                            fallback_connector.search_by_jurisdiction(
                                jurisdiction=jurisdiction,
                                start_date=query_start_date,
                                end_date=query_end_date,
                                positive_keywords=final_include_terms,
                                negative_keywords=final_exclude_terms,
                                patent_status_filter=patent_status_filter,
                                language=language_code,
                                limit=limit,
                                progress_callback=_on_keyword_search_progress,
                            )
                        )
                        provider_used = fallback_provider
                        fallback_reason = str(primary_exc)
                    except Exception as fallback_exc:
                        raise RuntimeError(
                            "Primary provider failed and fallback provider also failed. "
                            f"Primary error: {primary_exc} | Fallback error: {fallback_exc}"
                        ) from fallback_exc

                search_result["provider_used"] = provider_used
                if fallback_reason:
                    search_result["fallback_reason"] = fallback_reason

                set_cached_search_results(
                    cache=search_cache,
                    provider=selected_provider,
                    jurisdiction=jurisdiction,
                    start_date=query_start_date,
                    end_date=query_end_date,
                    positive_keywords=final_include_terms,
                    negative_keywords=final_exclude_terms,
                    patent_status_filter=patent_status_filter,
                    language=language_code,
                    limit=limit,
                    results=search_result,
                )

            patents = search_result.get("data", [])
            added_count = 0
            duplicate_count = 0

            for patent in patents:
                rid = (
                    patent.get("record_id")
                    or patent.get("lens_id")
                    or patent.get("epo_id")
                    or "UNKNOWN"
                )
                patent.setdefault("record_id", rid)
                patent.setdefault("lens_id", None)
                patent.setdefault("epo_id", None)
                patent.setdefault("provider_name", provider_used)
                patent.setdefault("provider_record_id", rid)
                patent.setdefault("is_fallback", provider_used != selected_provider)
                if fallback_reason:
                    patent.setdefault("fallback_reason", fallback_reason)

                if rid != "UNKNOWN" and rid in seen_record_ids:
                    duplicate_count += 1
                    continue
                if rid != "UNKNOWN":
                    seen_record_ids.add(rid)
                all_results.append(patent)
                added_count += 1

            diagnostics_entry = {
                "language": language_name,
                "provider": provider_used,
                "fallback_used": provider_used != selected_provider,
                "fallback_reason": fallback_reason,
                "from_cache": cached_result is not None,
                "query": search_result.get("query"),
                "query_strategy": search_result.get("query_strategy", "primary"),
                "endpoint_used": search_result.get("endpoint_used"),
                "total_available": search_result.get("total_available")
                or search_result.get("total_from_api"),
                "filtered_total": search_result.get("filtered_total", len(patents)),
                "added_unique": added_count,
                "duplicates_skipped": duplicate_count,
            }
            search_diagnostics.append(diagnostics_entry)

            _emit_progress(
                progress_callback,
                status_text=f"Search complete for {language_name} ({added_count} unique results)",
                progress_percent=10 + int((lang_idx + 1) * (35 / total_langs)),
                total_scanned=len(all_results),
            )

        except Exception as exc:
            logger.error("Search failed for %s: %s", language_name, exc)
            result_bundle.errors.append(f"Search failed for {language_name}: {exc}")
            continue

    result_bundle.raw_results = all_results
    result_bundle.search_diagnostics = search_diagnostics

    if not all_results:
        result_bundle.warnings.append(
            "No patents found matching your criteria across all selected languages."
        )
        return result_bundle

    _emit_progress(
        progress_callback,
        status_text=f"Scoring {len(all_results)} patents with {chosen_scoring_model} ({chosen_scoring_thinking})",
        progress_percent=50,
        total_scanned=len(all_results),
    )

    counts = {"high": 0, "medium": 0, "low": 0}

    def _on_analysis_progress(
        completed: int,
        total: int,
        msg: str,
        assessment: PatentAssessment | None,
    ) -> None:
        if assessment is not None:
            if assessment.intelligence_value == "HIGH":
                counts["high"] += 1
            elif assessment.intelligence_value == "MEDIUM":
                counts["medium"] += 1
            else:
                counts["low"] += 1
        pct = 50 + int((completed / total) * 45) if total > 0 else 50
        _emit_progress(
            progress_callback,
            status_text=msg,
            progress_percent=pct,
            total_scanned=total,
            high_count=counts["high"],
            medium_count=counts["medium"],
            low_count=counts["low"],
        )

    assessments = analyst.analyze_batch(all_results, progress_callback=_on_analysis_progress)
    dashboard = generator.create_dashboard_artifact(
        assessments=[a.to_dict() for a in assessments],
        jurisdictions=[jurisdiction] if jurisdiction else ["ALL"],
    )

    _emit_progress(
        progress_callback,
        status_text="Completed",
        progress_percent=100,
        total_scanned=dashboard.total_patents_searched,
        high_count=dashboard.high_priority_count,
        medium_count=dashboard.medium_priority_count,
        low_count=dashboard.low_priority_count,
    )

    result_bundle.assessments = assessments
    result_bundle.dashboard = dashboard
    return result_bundle
