import asyncio
import logging
import time
from types import SimpleNamespace

import streamlit as st

from project_aether.agents.analyst import AnalystAgent
from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords, translation_context
from project_aether.core.keyword_translation import (
    keyword_set_id,
    get_cached_translation,
    load_keyword_cache,
    ensure_keyword_set,
    save_keyword_cache,
    set_cached_translation,
    default_translation_for_language,
    translate_keywords_with_llm,
)
from project_aether.core.keywords import DEFAULT_KEYWORDS
from project_aether.tools.lens_api import LensConnector
from project_aether.ui.dashboard import render_metric_card, show_placeholder_dashboard
from project_aether.utils.artifacts import ArtifactGenerator

logger = logging.getLogger("ProjectAether")


def render_dashboard(dashboard_container, dashboard, status_text, progress_percent):
    """Render the dashboard summary cards."""
    with dashboard_container.container():
        if progress_percent <= 0:
            show_placeholder_dashboard()
            return

        dimmed = 0 < progress_percent < 100
        dim_style = "opacity: 0.6; filter: grayscale(0.35);" if dimmed else ""

        st.markdown(
            f"<div style=\"{dim_style}\">### Search Status: {status_text} (Ref: {dashboard.mission_id})</div>",
            unsafe_allow_html=True,
        )

        if dimmed:
            st.markdown(
                f"<div style=\"{dim_style}\">Progress: {progress_percent}%</div>",
                unsafe_allow_html=True,
            )
        else:
            st.progress(progress_percent)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_metric_card(
                "Total Results",
                str(dashboard.total_patents_searched),
                "Patents Scanned",
                "#94A3B8",
                dimmed=dimmed,
            )
        with col2:
            render_metric_card(
                "High Value",
                str(dashboard.high_priority_count),
                "Critical Findings",
                "#EF4444",
                dimmed=dimmed,
            )
        with col3:
            render_metric_card(
                "Medium Value",
                str(dashboard.medium_priority_count),
                "Potential Interest",
                "#F59E0B",
                dimmed=dimmed,
            )
        with col4:
            render_metric_card(
                "Low Value",
                str(dashboard.anomalous_count),
                "Probable Noise",
                "#00B4D8",
                dimmed=dimmed,
            )


def _build_dashboard_snapshot(total, high, medium, low, mission_id="IN-PROGRESS"):
    return SimpleNamespace(
        total_patents_searched=total,
        high_priority_count=high,
        medium_priority_count=medium,
        anomalous_count=low,
        mission_id=mission_id,
    )


def run_patent_search(language_codes, language_names, start_date, end_date, language_map):
    """Execute the patent search with specified languages, with live dashboard updates.
    
    Performs sequential searches for each language and accumulates all results.
    """

    # Create container for live dashboard
    dashboard_container = st.empty()

    try:
        render_dashboard(
            dashboard_container,
            _build_dashboard_snapshot(0, 0, 0, 0),
            "Initializing",
            5,
        )
        time.sleep(1)  # UX pacing

        config = get_config()
        connector = LensConnector()
        keyword_config = st.session_state.get("keyword_config", DEFAULT_KEYWORDS)
        cache = st.session_state.get("keyword_cache", load_keyword_cache())
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        ensure_keyword_set(cache, include_terms, exclude_terms)
        save_keyword_cache(cache)
        st.session_state["keyword_cache"] = cache
        analyst = AnalystAgent(keyword_config=keyword_config)
        generator = ArtifactGenerator()

        all_results = []
        
        # Perform searches for each selected language
        for lang_idx, (language_code, language_name) in enumerate(zip(language_codes, language_names)):
            render_dashboard(
                dashboard_container,
                _build_dashboard_snapshot(len(all_results), 0, 0, 0),
                f"Searching in {language_name} ({lang_idx + 1}/{len(language_codes)})",
                10 + (lang_idx * (25 / len(language_codes))),
            )
            
            # Determine which keywords to use based on language
            final_include_terms = include_terms
            final_exclude_terms = exclude_terms

            if language_name != "English":
                set_id = keyword_set_id(include_terms, exclude_terms)
                cached_translation = get_cached_translation(cache, set_id, language_name)
                
                if cached_translation:
                    # Use cached translation
                    final_include_terms = cached_translation.get("include", include_terms)
                    final_exclude_terms = cached_translation.get("exclude", exclude_terms)
                    render_dashboard(
                        dashboard_container,
                        _build_dashboard_snapshot(len(all_results), 0, 0, 0),
                        f"Using cached translations for {language_name}",
                        10 + (lang_idx * (25 / len(language_codes))),
                    )
                else:
                    # Translation not in cache - generate automatically
                    translation_successful = False
                    
                    # Try LLM translation if API key available
                    if config.google_api_key:
                        render_dashboard(
                            dashboard_container,
                            _build_dashboard_snapshot(len(all_results), 0, 0, 0),
                            f"Translating keywords to {language_name}...",
                            10 + (lang_idx * (25 / len(language_codes))),
                        )
                        try:
                            final_include_terms, final_exclude_terms = translate_keywords_with_llm(
                                include_terms=include_terms,
                                exclude_terms=exclude_terms,
                                target_language=language_name,
                                context=translation_context(),
                                api_key=config.google_api_key,
                            )
                            # Save the translation to cache
                            set_cached_translation(
                                cache,
                                set_id=set_id,
                                language=language_name,
                                include_terms=final_include_terms,
                                exclude_terms=final_exclude_terms,
                                source="llm",
                            )
                            translation_successful = True
                            logger.info(f"Translated keywords to {language_name} using LLM")
                        except Exception as exc:
                            logger.warning(f"LLM translation failed for {language_name}: {exc}")
                    
                    # Fall back to default translations if LLM failed or unavailable
                    if not translation_successful:
                        fallback = default_translation_for_language(language_name)
                        if fallback:
                            final_include_terms, final_exclude_terms = fallback
                            # Save the default translation to cache
                            set_cached_translation(
                                cache,
                                set_id=set_id,
                                language=language_name,
                                include_terms=final_include_terms,
                                exclude_terms=final_exclude_terms,
                                source="default",
                            )
                            logger.info(f"Using default translations for {language_name}")
                        else:
                            logger.warning(f"No translation available for {language_name}, using English terms")
                    
                    # Save updated cache
                    save_keyword_cache(cache)
                    st.session_state["keyword_cache"] = cache

            try:
                # No jurisdiction filtering - search all with specified language
                result = asyncio.run(
                    connector.search_by_jurisdiction(
                        jurisdiction=None,
                        start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
                        end_date=end_date.strftime("%Y-%m-%d"),
                        positive_keywords=final_include_terms,
                        negative_keywords=final_exclude_terms,
                        language=language_code,
                    )
                )
                patents = result.get("data", [])
                all_results.extend(patents)
                logger.info(f"Found {len(patents)} patents for {language_name}")
            except Exception as exc:
                logger.error(f"Search failed for {language_name}: {exc}")
                st.error(f"Search failed for {language_name}: {exc}")
                continue

        st.session_state["all_raw_results"] = all_results

        if not all_results:
            st.warning("No patents found matching your criteria across all selected languages.")
            return

        render_dashboard(
            dashboard_container,
            _build_dashboard_snapshot(len(all_results), 0, 0, 0),
            f"Analyzing {len(all_results)} patents from {len(language_names)} language(s)",
            50,
        )

        # Analyze patents incrementally and update dashboard in real-time
        assessments = []
        high_count = 0
        medium_count = 0
        low_count = 0

        for i, patent_record in enumerate(all_results):
            try:
                assessment = analyst.analyze_patent(patent_record)
                assessments.append(assessment)

                # Count by intelligence value
                if assessment.intelligence_value == "HIGH":
                    high_count += 1
                elif assessment.intelligence_value == "MEDIUM":
                    medium_count += 1
                else:
                    low_count += 1

                # Update dashboard every patent (or every N patents for performance)
                if (i + 1) % max(1, len(all_results) // 10) == 0 or (i + 1) == len(all_results):
                    # Update status using dashboard renderer
                    percent_done = int(50 + ((i + 1) / len(all_results)) * 45)
                    render_dashboard(
                        dashboard_container,
                        _build_dashboard_snapshot(i + 1, high_count, medium_count, low_count),
                        f"Analyzing ({i + 1}/{len(all_results)})",
                        percent_done,
                    )

                    if assessment.intelligence_value == "HIGH":
                        logger.info(
                            f"HIGH VALUE TARGET: {assessment.lens_id} "
                            f"({assessment.jurisdiction}) - {assessment.summary}"
                        )

            except Exception as exc:
                logger.error(f"Failed to analyze patent: {exc}")

        render_dashboard(
            dashboard_container,
            _build_dashboard_snapshot(len(all_results), high_count, medium_count, low_count),
            "Finalizing",
            95,
        )

        # Create final dashboard artifact
        dashboard = generator.create_dashboard_artifact(
            assessments=[a.to_dict() for a in assessments],
            jurisdictions=["ALL"],
        )

        st.session_state["assessments"] = assessments
        st.session_state["dashboard"] = dashboard        

        # Render final dashboard
        render_dashboard(dashboard_container, dashboard, "Completed", 100)

        st.rerun()

    except ImportError as exc:
        st.error(f"System Error: Dependency missing ({exc}). Run `uv sync`.")
    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        logger.error(f"Analysis failed: {exc}", exc_info=True)
