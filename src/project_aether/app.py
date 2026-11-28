"""
Project Aether - Patent Intelligence Workbench
Main Streamlit application entry point.
"""

import html
import logging

import streamlit as st

from project_aether.agents.analyst import AnalystAgent
from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.keyword_translation import (
    get_history_entries,
    load_keyword_cache,
)
from project_aether.core.llm import (
    SUPPORTED_MODELS,
    THINKING_LEVELS,
    QuotaExhaustedError,
)
from project_aether.core.llm_scoring import DEFAULT_SCORING_SYSTEM_PROMPT
from project_aether.core.log_stream import install_log_stream_handler
from project_aether.core.reviews import build_calibration_prompt_block
from project_aether.core.scoring_cache import (
    clear_scoring_cache,
    get_scoring_cache_stats,
)
from project_aether.core.search_cache import clear_search_cache, get_search_cache_stats
from project_aether.core.translation_service import (
    clear_translation_cache,
    get_translation_cache_stats,
)
from project_aether.services.search import execute_patent_search
from project_aether.tools.inpadoc import INPADOC_CODES
from project_aether.ui.analysis import render_deep_dive_tab
from project_aether.ui.dashboard import (
    render_dashboard_metrics,
    render_dashboard_progress,
    show_placeholder_dashboard,
)
from project_aether.ui.logs import render_live_logs_tab
from project_aether.ui.results import render_results_tab
from project_aether.ui.reviews import render_reviews_tab
from project_aether.ui.sidebar import render_sidebar
from project_aether.ui.styles import inject_global_styles
from project_aether.utils.artifacts import ArtifactGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,
    handlers=[logging.StreamHandler()],
)
for _noisy_logger in (
    "httpcore",
    "httpcore2",
    "httpx",
    "httpx2",
    "google_genai",
    "google_genai.models",
    "urllib3",
    "asyncio",
):
    logging.getLogger(_noisy_logger).setLevel(logging.WARNING)
logger = logging.getLogger("ProjectAether")

install_log_stream_handler(max_entries=10000, level=logging.INFO)
logging.getLogger("LensConnector").setLevel(logging.INFO)
logging.getLogger("EPOConnector").setLevel(logging.INFO)

JURISDICTION_MAP = {
    "All": "ALL",
    "European Patents": "EP",
    "China": "CN",
    "Japan": "JP",
    "United States": "US",
    "Germany": "DE",
    "Republic of Korea": "KR",
    "United Kingdom": "GB",
    "France": "FR",
    "Canada": "CA",
    "Russia": "RU",
    "Poland": "PL",
    "Romania": "RO",
    "Czech Republic": "CZ",
    "Netherlands": "NL",
    "Spain": "ES",
    "Italy": "IT",
    "Sweden": "SE",
    "Norway": "NO",
    "Finland": "FI",
    "Hungary": "HU",
}

LANGUAGE_MAP = {
    "English": "EN",
    "German": "DE",
    "Chinese": "ZH",
    "Japanese": "JA",
    "Korean": "KO",
    "French": "FR",
    "Russian": "RU",
    "Spanish": "ES",
    "Portuguese": "PT",
    "Italian": "IT",
    "Swedish": "SV",
    "Norwegian": "NO",
    "Finnish": "FI",
    "Polish": "PL",
    "Romanian": "RO",
    "Czech": "CS",
    "Dutch": "NL",
    "Arabic": "AR",
    "Hungarian": "HU",
}

st.set_page_config(
    page_title="Project Aether",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()


def _init_session_state() -> None:
    cfg = get_config()
    defaults = {
        "keyword_cache": load_keyword_cache(),
        "keyword_config": {"English": {"positive": [], "negative": []}},
        "keyword_widget_version": 0,
        "relevance_threshold": 40,
        "high_priority_threshold": 70,
        "patents_per_language": 1000,
        "use_calibration_examples": True,
        "llm_scoring_model": cfg.llm_scoring_model,
        "llm_scoring_thinking_level": cfg.llm_scoring_thinking_level,
        "llm_keyword_model": cfg.llm_keyword_model,
        "llm_keyword_thinking_level": cfg.llm_keyword_thinking_level,
        "llm_translation_model": cfg.llm_translation_model,
        "llm_translation_thinking_level": cfg.llm_translation_thinking_level,
        "llm_brief_model": cfg.llm_brief_model,
        "llm_brief_thinking_level": cfg.llm_brief_thinking_level,
        "llm_advisor_model": cfg.llm_advisor_model,
        "llm_advisor_thinking_level": cfg.llm_advisor_thinking_level,
        "llm_scoring_system_prompt": DEFAULT_SCORING_SYSTEM_PROMPT,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if "keyword_set_loaded" not in st.session_state:
        cache = st.session_state["keyword_cache"]
        history_entries = get_history_entries(cache)
        if history_entries:
            most_recent = history_entries[0]
            st.session_state["keyword_config"].setdefault("English", {})["positive"] = most_recent.get("include", [])
            st.session_state["keyword_config"].setdefault("English", {})["negative"] = most_recent.get("exclude", [])
            st.session_state["keyword_set_name"] = most_recent.get("label", "")
            st.session_state["keyword_set_mode"] = "UPDATE"
            st.session_state["keyword_set_update_id"] = most_recent.get("id")
            st.session_state["keyword_set_original_include"] = most_recent.get("include", [])
            st.session_state["keyword_set_original_exclude"] = most_recent.get("exclude", [])
        else:
            st.session_state["keyword_set_mode"] = "SAVE"
            st.session_state["keyword_set_update_id"] = None
            st.session_state["keyword_set_original_include"] = []
            st.session_state["keyword_set_original_exclude"] = []
        st.session_state["keyword_set_loaded"] = True


def _model_select(label: str, state_key: str) -> None:
    current = st.session_state.get(state_key, SUPPORTED_MODELS[0])
    options = list(SUPPORTED_MODELS)
    if current not in options:
        options.insert(0, current)
    st.selectbox(label, options=options, key=state_key)


def _thinking_select(label: str, state_key: str) -> None:
    current = st.session_state.get(state_key, "low")
    options = list(THINKING_LEVELS)
    if current not in options:
        st.session_state[state_key] = options[0]
    st.selectbox(label, options=options, key=state_key)


def _render_masthead(config) -> None:
    primary = config.normalized_patent_provider
    secondary = "lens" if primary == "epo" else "epo"
    labels = {"epo": "EPO OPS", "lens": "Lens"}
    available = {"epo": config.is_epo_configured, "lens": config.is_lens_configured}

    p_dot = "aether-dot--ok" if available[primary] else "aether-dot--err"
    s_dot = "aether-dot--ok" if available[secondary] else "aether-dot--warn"
    g_dot = "aether-dot--ok" if config.is_llm_configured else "aether-dot--warn"

    p_label = html.escape(labels[primary])
    s_label = html.escape(labels[secondary])
    g_text = "Gemini ready" if config.is_llm_configured else "Gemini offline"

    st.markdown(
        f"""
        <div class="aether-masthead">
            <div class="aether-brand">
                <span class="aether-wordmark">Project Aether</span>
                <span class="aether-tagline">Patent intelligence workbench</span>
            </div>
            <div class="aether-status-strip">
                <span class="aether-status-item"><span class="aether-dot {p_dot}"></span>{p_label}</span>
                <span class="aether-status-item"><span class="aether-dot {s_dot}"></span>{s_label} fallback</span>
                <span class="aether-status-item"><span class="aether-dot {g_dot}"></span>{g_text}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _init_session_state()

    (
        config,
        selected_language_codes,
        selected_language_names,
        start_date,
        end_date,
        selected_jurisdiction,
        selected_statuses,
        force_refresh,
        run_mission,
    ) = render_sidebar(LANGUAGE_MAP, JURISDICTION_MAP)

    _render_masthead(config)

    tab_dashboard, tab_results, tab_analysis, tab_reviews, tab_settings, tab_live_logs = st.tabs(
        [
            "Dashboard",
            "Search Results",
            "Detailed Analysis",
            "Reviewed Patents",
            "Settings",
            "Logs",
        ]
    )

    # --- DASHBOARD TAB ---
    with tab_dashboard:
        dashboard_container = st.empty()

        if run_mission:
            if not config.is_epo_configured and not config.is_lens_configured:
                st.error("Analysis aborted: both Lens primary provider and EPO fallback are unconfigured.")
            else:
                if not config.is_patent_provider_configured and config.is_fallback_provider_configured:
                    st.warning(
                        f"Primary provider ({config.normalized_patent_provider.upper()}) unavailable. "
                        "Running with fallback provider."
                    )
                st.session_state.pop("dashboard", None)
                try:
                    run_result = execute_patent_search(
                        language_codes=selected_language_codes,
                        language_names=selected_language_names,
                        keyword_config=st.session_state["keyword_config"],
                        keyword_cache=st.session_state["keyword_cache"],
                        start_date=start_date,
                        end_date=end_date,
                        jurisdiction=selected_jurisdiction,
                        patent_status_filter=selected_statuses,
                        patents_per_language=st.session_state["patents_per_language"],
                        scoring_model=st.session_state["llm_scoring_model"],
                        scoring_thinking_level=st.session_state["llm_scoring_thinking_level"],
                        scoring_system_prompt=st.session_state["llm_scoring_system_prompt"],
                        keyword_model=st.session_state["llm_keyword_model"],
                        keyword_thinking_level=st.session_state["llm_keyword_thinking_level"],
                        relevance_threshold=st.session_state["relevance_threshold"],
                        high_threshold=st.session_state["high_priority_threshold"],
                        use_calibration_examples=st.session_state["use_calibration_examples"],
                        force_refresh_search=force_refresh,
                        progress_callback=lambda ev: render_dashboard_progress(dashboard_container, ev),
                    )
                    for err in run_result.errors:
                        st.error(err)
                    for warn in run_result.warnings:
                        st.warning(warn)

                    st.session_state["keyword_cache"] = run_result.keyword_cache
                    st.session_state["all_raw_results"] = run_result.raw_results
                    st.session_state["search_diagnostics"] = run_result.search_diagnostics
                    if run_result.assessments:
                        st.session_state["assessments"] = run_result.assessments
                        st.session_state["dashboard"] = run_result.dashboard
                        st.rerun()
                except QuotaExhaustedError:
                    st.error(
                        "API quota exceeded: Gemini API daily quota is exhausted. "
                        "Try again later or check https://ai.dev/rate-limit."
                    )
                except Exception as exc:
                    st.error(f"Analysis failed: {exc}")
                    logger.exception("Analysis failed")
        else:
            dashboard_state = st.session_state.get("dashboard")
            with dashboard_container.container():
                if dashboard_state:
                    render_dashboard_metrics(
                        dashboard_state,
                        assessments=st.session_state.get("assessments"),
                    )
                else:
                    inc_terms, exc_terms = get_active_english_keywords(
                        st.session_state.get("keyword_config", {})
                    )
                    inc_count = (
                        sum(len(g) for g in inc_terms)
                        if inc_terms and isinstance(inc_terms[0], list)
                        else len(inc_terms)
                    )
                    show_placeholder_dashboard(
                        keyword_set_name=st.session_state.get("keyword_set_name", ""),
                        include_count=inc_count,
                        exclude_count=len(exc_terms),
                        languages=selected_language_names,
                    )

    # --- RESULTS TAB ---
    with tab_results:
        render_results_tab(st.session_state.get("assessments"), JURISDICTION_MAP)

    # --- ANALYSIS TAB ---
    with tab_analysis:
        render_deep_dive_tab(st.session_state.get("assessments"))

    # --- REVIEWED PATENTS TAB ---
    with tab_reviews:
        render_reviews_tab()

    # --- LOGS TAB ---
    with tab_live_logs:
        render_live_logs_tab()

    # --- SETTINGS TAB ---
    with tab_settings:
        st.markdown("### Triage thresholds")
        p1, p2, p3 = st.columns(3, vertical_alignment="top")
        with p1:
            st.slider(
                "Medium relevance threshold",
                0,
                100,
                key="relevance_threshold",
                help="Patents below this score are classified as LOW priority (unless substantively refused).",
            )
        with p2:
            st.slider(
                "High priority threshold",
                0,
                100,
                key="high_priority_threshold",
                help="Patents at or above this score are classified as HIGH priority.",
            )
        with p3:
            patents_per_language = st.slider(
                "Max patents per language",
                1,
                1000,
                key="patents_per_language",
                help="Set to 1000 for unlimited retrieval per language.",
            )
            if patents_per_language >= 1000:
                st.caption("Unlimited retrieval per language.")
            else:
                st.caption(f"Capped at {patents_per_language} patents per language.")

        st.markdown("---")
        st.markdown("### Model and thinking configuration")
        st.caption(
            "Defaults use `gemini-4-hydrogen` with task-tuned thinking levels: `low` for high-volume "
            "scoring and translation, `medium` for keyword translation and query advice, and `high` for deep briefs."
        )

        task_rows = [
            ("Bulk patent scoring", "llm_scoring_model", "llm_scoring_thinking_level"),
            ("Keyword translation", "llm_keyword_model", "llm_keyword_thinking_level"),
            ("Abstract translation", "llm_translation_model", "llm_translation_thinking_level"),
            ("Deep technical brief", "llm_brief_model", "llm_brief_thinking_level"),
            ("Query advisor", "llm_advisor_model", "llm_advisor_thinking_level"),
        ]
        for task_label, m_key, t_key in task_rows:
            c1, c2 = st.columns([2, 1.15], vertical_alignment="bottom")
            with c1:
                _model_select(f"{task_label} · Model", m_key)
            with c2:
                _thinking_select(f"{task_label} · Thinking", t_key)

        if st.button("Reset LLM defaults"):
            st.session_state["llm_scoring_model"] = config.llm_scoring_model
            st.session_state["llm_scoring_thinking_level"] = config.llm_scoring_thinking_level
            st.session_state["llm_keyword_model"] = config.llm_keyword_model
            st.session_state["llm_keyword_thinking_level"] = config.llm_keyword_thinking_level
            st.session_state["llm_translation_model"] = config.llm_translation_model
            st.session_state["llm_translation_thinking_level"] = config.llm_translation_thinking_level
            st.session_state["llm_brief_model"] = config.llm_brief_model
            st.session_state["llm_brief_thinking_level"] = config.llm_brief_thinking_level
            st.session_state["llm_advisor_model"] = config.llm_advisor_model
            st.session_state["llm_advisor_thinking_level"] = config.llm_advisor_thinking_level
            st.session_state["llm_scoring_system_prompt"] = DEFAULT_SCORING_SYSTEM_PROMPT
            st.rerun()

        st.markdown("---")
        st.markdown("### Scoring prompt and calibration")
        st.checkbox(
            "Inject reviewed patents as few-shot calibration examples",
            key="use_calibration_examples",
        )
        st.text_area(
            "Scoring system prompt",
            key="llm_scoring_system_prompt",
            height=220,
        )
        st.caption(
            "Placeholders: `{positive_keywords}`, `{negative_keywords}`, and `{calibration_examples}`."
        )

        raw_results = st.session_state.get("all_raw_results", [])
        if raw_results and st.button("Re-score current results with latest settings", type="primary"):
            try:
                cal = build_calibration_prompt_block() if st.session_state["use_calibration_examples"] else ""
                analyst = AnalystAgent(
                    keyword_config=st.session_state["keyword_config"],
                    scoring_system_prompt=st.session_state["llm_scoring_system_prompt"],
                    scoring_model=st.session_state["llm_scoring_model"],
                    scoring_thinking_level=st.session_state["llm_scoring_thinking_level"],
                    relevance_threshold=st.session_state["relevance_threshold"],
                    high_threshold=st.session_state["high_priority_threshold"],
                    calibration_examples=cal,
                )
                with st.spinner(f"Re-scoring {len(raw_results)} patents..."):
                    assessments = analyst.analyze_batch(raw_results)
                dashboard = ArtifactGenerator().create_dashboard_artifact(
                    assessments=[a.to_dict() for a in assessments],
                    jurisdictions=["ALL"],
                )
                st.session_state["assessments"] = assessments
                st.session_state["dashboard"] = dashboard
                st.success(f"Re-scored {len(assessments)} patents.")
                st.rerun()
            except QuotaExhaustedError:
                st.error("Gemini API quota exceeded during re-scoring.")

        st.markdown("---")
        st.markdown("### Local cache storage")
        s_stats = get_search_cache_stats()
        sc_stats = get_scoring_cache_stats()
        tr_stats = get_translation_cache_stats()
        s_unit = "file" if s_stats["entries"] == 1 else "files"
        sc_unit = "entry" if sc_stats["entries"] == 1 else "entries"
        tr_unit = "entry" if tr_stats["entries"] == 1 else "entries"
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.markdown(
                f"""
                <div class="aether-metric-card" style="--card-accent: #475569;">
                    <div class="aether-metric-label">Search cache</div>
                    <div class="aether-metric-value">{s_stats['entries']:,}</div>
                    <div class="aether-metric-sub">{s_unit} · {s_stats['size_bytes'] / 1024:.1f} KB · JSON</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Clear search cache", width="stretch"):
                removed = clear_search_cache()
                st.success(f"Removed {removed} search cache file(s).")
        with cc2:
            st.markdown(
                f"""
                <div class="aether-metric-card" style="--card-accent: #2563EB;">
                    <div class="aether-metric-label">Scoring cache</div>
                    <div class="aether-metric-value">{sc_stats['entries']:,}</div>
                    <div class="aether-metric-sub">{sc_unit} · {sc_stats['size_bytes'] / 1024:.1f} KB · JSONL</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Clear scoring cache", width="stretch"):
                removed = clear_scoring_cache()
                st.success(f"Cleared {removed} scoring cache entry/entries.")
        with cc3:
            st.markdown(
                f"""
                <div class="aether-metric-card" style="--card-accent: #059669;">
                    <div class="aether-metric-label">Translation cache</div>
                    <div class="aether-metric-value">{tr_stats['entries']:,}</div>
                    <div class="aether-metric-sub">{tr_unit} · {tr_stats['size_bytes'] / 1024:.1f} KB · JSONL</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Clear translation cache", width="stretch"):
                removed = clear_translation_cache()
                st.success(f"Cleared {removed} translation cache entry/entries.")

        st.markdown("---")
        with st.expander("Search diagnostics", expanded=False):
            diagnostics = st.session_state.get("search_diagnostics", [])
            if diagnostics:
                st.json(diagnostics)
            else:
                st.caption("No search diagnostics available yet. Run a search to populate this panel.")

        with st.expander("INPADOC status codes reference", expanded=False):
            jurisdictions = list(INPADOC_CODES.keys())
            if jurisdictions:
                jur_tabs = st.tabs(jurisdictions)
                for jur, tab in zip(jurisdictions, jur_tabs):
                    with tab:
                        codes = INPADOC_CODES[jur]
                        for code, details in codes.items():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"`{code}`")
                            with col2:
                                st.markdown(f"{details['description']}")
                                st.caption(f"Severity: {details['severity'].value}")


if __name__ == "__main__":
    main()
