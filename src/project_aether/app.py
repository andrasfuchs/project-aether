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
        if run_mission:
            # Check API configuration
            if not config.is_lens_configured:
                st.error("Analysis aborted: Lens.org API disconnected")
            else:
                run_patent_search(selected_language_codes, selected_language_names, start_date, end_date, LANGUAGE_MAP)
        else:
            dashboard_state = st.session_state.get('dashboard')
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
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="glass-card">
                <h4>API Connections</h4>
                <p>Manage external services.</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="glass-card">
                <h4>Model Parameters</h4>
                <p>Fine-tune relevance thresholds.</p>
            </div>
            """, unsafe_allow_html=True)
            
            relevance_threshold = st.slider("Relevance Threshold", 0, 100, 40)
            st.caption(f"Patents below {relevance_threshold}% relevance will be classified as LOW intelligence.")

        st.markdown("---")
        st.markdown("### Keyword Database")
        st.info("Configure the lexicon used to detect anomalies and filter false positives.")
        
        # Dynamic Keyword Editor
        if 'keyword_config' in st.session_state:
            kw_config = st.session_state['keyword_config']
            
            # Language Selector (Tabs)
            languages = list(kw_config.keys())
            if not languages:
                st.warning("No languages configured.")
            else:
                lang_tabs = st.tabs([f"{l}" for l in languages])
                
                for lang, tab in zip(languages, lang_tabs):
                    with tab:
                        c1, c2 = st.columns(2)
                        
                        with c1:
                            st.markdown(f"#### Include Keywords")
                            st.caption("Terms indicating anomalous energy phenomena")
                            current_pos = kw_config[lang].get('positive', [])
                            new_pos = st.text_area(
                                "Comma-separated values",
                                value=", ".join(current_pos),
                                height=300,
                                key=f"pos_{lang}",
                                label_visibility="collapsed"
                            )
                            kw_config[lang]['positive'] = [x.strip() for x in new_pos.split(",") if x.strip()]
                            
                        with c2:
                            st.markdown(f"#### Exclude Keywords")
                            st.caption("Terms indicating standard industrial technology")
                            current_neg = kw_config[lang].get('negative', [])
                            new_neg = st.text_area(
                                "Comma-separated values",
                                value=", ".join(current_neg),
                                height=300,
                                key=f"neg_{lang}",
                                label_visibility="collapsed"
                            )
                            kw_config[lang]['negative'] = [x.strip() for x in new_neg.split(",") if x.strip()]



if __name__ == "__main__":
    main()
