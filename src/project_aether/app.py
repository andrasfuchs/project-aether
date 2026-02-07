"""
Project Aether - Agentic Patent Intelligence Framework
Main Streamlit application entry point.
"""

import streamlit as st
import logging
import copy
from project_aether.core.keywords import DEFAULT_KEYWORDS
from project_aether.core.keyword_translation import (
    load_keyword_cache,
    get_history_entries,
)
from project_aether.services.search import run_patent_search
from project_aether.ui.dashboard import render_dashboard_metrics, show_placeholder_dashboard
from project_aether.ui.analysis import render_deep_dive_tab
from project_aether.ui.results import render_results_tab
from project_aether.ui.sidebar import render_sidebar
from project_aether.ui.styles import inject_global_styles
from project_aether.tools.inpadoc import INPADOC_CODES

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG to see debug messages
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Force reconfiguration even if logging was already configured
    handlers=[
        logging.StreamHandler()  # Ensure output goes to console/terminal
    ]
)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("ProjectAether")

# Explicitly set the LensConnector logger to DEBUG
logging.getLogger("LensConnector").setLevel(logging.DEBUG)

# Jurisdiction mapping: Display Name -> ISO Code(s)
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
    "Hungary": "HU"
}

JURISDICTION_LANGUAGE_MAP = {
    "CN": "Chinese",
    "JP": "Japanese",
    "KR": "Korean",
    "DE": "German",
    "FR": "French",
    "ES": "Spanish",
    "IT": "Italian",
    "SE": "Swedish",
    "NO": "Norwegian",
    "FI": "Finnish",
    "RU": "Russian",
    "PL": "Polish",
    "RO": "Romanian",
    "CZ": "Czech",
    "NL": "Dutch",
    "GB": "English",
    "US": "English",
    "CA": "English",
    "EP": "English",
    "HU": "Hungarian",
}

# Language mapping: Display Name -> Lens API Code
LANGUAGE_MAP = {
    "English": "EN",
    "Chinese": "ZH",
    "Japanese": "JA",
    "Korean": "KO",
    "French": "FR", 
    "Russian": "RU",
    "Spanish": "ES",
    "Portuguese": "PT",
    "Dutch": "DE",
    "Arabic": "AR",
    "Other": "Other",
}

# Page configuration
st.set_page_config(
    page_title="Project Aether",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- MODERN UI / CSS INJECTION ---
inject_global_styles()


def main():
    """Main application entry point."""
    
    # Initialize Session State for Keywords if not present
    if 'keyword_config' not in st.session_state:
        st.session_state['keyword_config'] = copy.deepcopy(DEFAULT_KEYWORDS)
    if 'keyword_cache' not in st.session_state:
        st.session_state['keyword_cache'] = load_keyword_cache()
    if 'keyword_widget_version' not in st.session_state:
        st.session_state['keyword_widget_version'] = 0
    
    # Load the most recently used keyword set if available
    if 'keyword_set_loaded' not in st.session_state:
        cache = st.session_state['keyword_cache']
        history_entries = get_history_entries(cache)
        if history_entries:
            most_recent = history_entries[0]
            st.session_state['keyword_config'].setdefault("English", {})["positive"] = most_recent.get("include", [])
            st.session_state['keyword_config'].setdefault("English", {})["negative"] = most_recent.get("exclude", [])
            st.session_state['keyword_set_name'] = most_recent.get("label", "")
            
            # Set to UPDATE mode since we're loading an existing keyword set
            st.session_state['keyword_set_mode'] = "UPDATE"
            st.session_state['keyword_set_update_id'] = most_recent.get("id")
            st.session_state['keyword_set_original_include'] = most_recent.get("include", [])
            st.session_state['keyword_set_original_exclude'] = most_recent.get("exclude", [])
        st.session_state['keyword_set_loaded'] = True
    
    # --- HEADER SECTION ---
    st.markdown("""
    <div class="header-container">
        <div class="main-title">Project Aether</div>
        <div class="subtitle">Rejected today, revolutionary tomorrow</div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- SIDEBAR CONFIGURATION ---
    config, selected_language_codes, selected_language_names, start_date, end_date, run_mission = render_sidebar(LANGUAGE_MAP)

    # --- MAIN CONTENT TABS ---
    tab_dashboard, tab_results, tab_analysis, tab_settings = st.tabs([
        "Dashboard",
        "Search Results",
        "Detailed Analysis",
        "Settings"
    ])
    
    # --- DASHBOARD TAB ---
    with tab_dashboard:
        # Create container for dashboard (will be reused for live updates during search)
        dashboard_container = st.empty()
        
        if run_mission:
            # Check API configuration
            if not config.is_lens_configured:
                st.error("Analysis aborted: Lens.org API disconnected")
            else:
                # Clear old dashboard state before starting new search
                if 'dashboard' in st.session_state:
                    del st.session_state['dashboard']
                # Pass the container to run_patent_search - it will manage all updates
                run_patent_search(selected_language_codes, selected_language_names, start_date, end_date, LANGUAGE_MAP, dashboard_container)
        else:
            # Only render dashboard if not currently searching
            dashboard_state = st.session_state.get('dashboard')
            with dashboard_container.container():
                if dashboard_state:
                    # Render existing dashboard data
                    render_dashboard_metrics(dashboard_state)
                else:
                    # Show placeholder dashboard
                    show_placeholder_dashboard()
    
    # --- RESULTS TAB ---
    with tab_results:
        render_results_tab(st.session_state.get("assessments"), JURISDICTION_MAP)

    # --- ANALYSIS TAB ---
    with tab_analysis:
        render_deep_dive_tab(st.session_state.get("assessments"))

    # --- SETTINGS TAB ---
    with tab_settings:
        st.markdown("### System Parameters")
        
        relevance_threshold = st.slider("Relevance Threshold", 0, 100, 40)
        st.caption(f"Patents below {relevance_threshold}% relevance will be classified as LOW intelligence.")

        patents_per_language = st.slider(
            "Patents Per Language",
            1,
            1000,
            10,
            key="patents_per_language",
        )
        if patents_per_language >= 1000:
            st.caption("No limit will be applied to results per language.")
        else:
            st.caption(f"Limits results to {patents_per_language} patents per language.")

        st.markdown("---")
        st.markdown("### Analyst Overview")
        st.markdown(
            """
            - **Legal status forensics**: decodes INPADOC events and patent status to assign a
              severity level (HIGH/MEDIUM/LOW/UNKNOWN).
            - **Relevance score (0–100)**: keyword-based scoring on title + abstract + claims,
              with boosts for hydrogen/plasma terms and penalties for false positives.
            - **Anomalous detection**: flags over-unity or anomalous-phenomena terminology.
            - **Classification tags**: extracts high-value IPC/CPC symbols (e.g., fusion/plasma groups).
            - **Intelligence value**: combines severity, relevance, anomaly flag, and tags to rate
              each patent as HIGH, MEDIUM, or LOW priority.
            """
        )

        st.markdown("---")
        st.markdown("### INPADOC Status Codes")
        st.info("Known patent legal status codes used for forensic analysis by jurisdiction.")

        # Create tabs for each jurisdiction
        jurisdictions = list(INPADOC_CODES.keys())
        if jurisdictions:
            jur_tabs = st.tabs(jurisdictions)

            for jur, tab in zip(jurisdictions, jur_tabs):
                with tab:
                    codes = INPADOC_CODES[jur]
                    if codes:
                        for code, details in codes.items():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.markdown(f"**{code}**")
                            with col2:
                                st.markdown(f"{details['description']}")
                                st.caption(f"*Severity: {details['severity'].value}*")
                    else:
                        st.write("No codes configured for this jurisdiction.")
if __name__ == "__main__":
    main()
