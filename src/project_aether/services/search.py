import asyncio
import logging
import time
from types import SimpleNamespace

import streamlit as st

from project_aether.agents.analyst import AnalystAgent
from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.keyword_translation import (
    keyword_set_id,
    get_cached_translation,
    load_keyword_cache,
    ensure_keyword_set,
    save_keyword_cache,
)
from project_aether.core.keywords import DEFAULT_KEYWORDS
from project_aether.tools.lens_api import LensConnector
from project_aether.ui.dashboard import render_metric_card
from project_aether.utils.artifacts import ArtifactGenerator

logger = logging.getLogger("ProjectAether")


def render_dashboard(dashboard_container, dashboard, status_text, progress_percent):
    """Render the dashboard summary cards."""
    with dashboard_container.container():
        st.markdown(f"### Search Status: {status_text} (Ref: {dashboard.mission_id})")

        st.progress(progress_percent)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_metric_card(
                "Total Results", str(dashboard.total_patents_searched), "Patents Scanned", "#94A3B8"
            )
        with col2:
            render_metric_card(
                "High Value", str(dashboard.high_priority_count), "Critical Findings", "#EF4444"
            )
        with col3:
            render_metric_card(
                "Medium Value", str(dashboard.medium_priority_count), "Potential Interest", "#F59E0B"
            )
        with col4:
            render_metric_card("Low Value", str(dashboard.anomalous_count), "Probable Noise", "#00B4D8")


def _build_dashboard_snapshot(total, high, medium, low, mission_id="IN-PROGRESS"):
    return SimpleNamespace(
        total_patents_searched=total,
        high_priority_count=high,
        medium_priority_count=medium,
        anomalous_count=low,
        mission_id=mission_id,
    )


def run_patent_search(language_code, start_date, end_date, language_map):
    """Execute the patent search with specified language, with live dashboard updates."""

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

        # Determine which keywords to use based on language
        search_language_name = None
        for display_name, code in language_map.items():
            if code == language_code and display_name != "Other":
                search_language_name = display_name
                break

        # If language is not English, try to get translated keywords
        final_include_terms = include_terms
        final_exclude_terms = exclude_terms

        if search_language_name and search_language_name != "English":
            set_id = keyword_set_id(include_terms, exclude_terms)
            cached_translation = get_cached_translation(cache, set_id, search_language_name)
            if cached_translation:
                final_include_terms = cached_translation.get("include", include_terms)
                final_exclude_terms = cached_translation.get("exclude", exclude_terms)
                render_dashboard(
                    dashboard_container,
                    _build_dashboard_snapshot(0, 0, 0, 0),
                    f"Using cached translations for {search_language_name}",
                    10,
                )

        all_results = []
        render_dashboard(
            dashboard_container,
            _build_dashboard_snapshot(0, 0, 0, 0),
            f"Searching in {search_language_name or language_code}",
            33,
        )

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
        except Exception as exc:
            logger.error(f"Search failed: {exc}")
            st.error(f"Search failed: {exc}")
            return

        st.session_state["all_raw_results"] = all_results

        if not all_results:
            st.warning("No patents found matching your criteria.")
            return

        render_dashboard(
            dashboard_container,
            _build_dashboard_snapshot(0, 0, 0, 0),
            f"In Progress (0/{len(all_results)})",
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
                        f"In Progress ({i + 1}/{len(all_results)})",
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
