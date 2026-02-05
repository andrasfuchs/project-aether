"""
Project Aether - Agentic Patent Intelligence Framework
Main Streamlit application entry point.
"""

import streamlit as st
import logging
from datetime import datetime, timedelta
import time
import asyncio
import copy
from typing import List, Optional
from project_aether.core.keywords import DEFAULT_KEYWORDS
from project_aether.core.keyword_translation import (
    load_keyword_cache,
    save_keyword_cache,
    ensure_keyword_set,
    get_cached_translation,
    set_cached_translation,
    keyword_set_id,
    normalize_terms,
    default_translation_for_language,
    translate_keywords_with_llm,
    get_history_entries,
    delete_keyword_set,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO to DEBUG to see debug messages
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Force reconfiguration even if logging was already configured
    handlers=[
        logging.StreamHandler()  # Ensure output goes to console/terminal
    ]
)
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
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    /* Base Styles */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Global Background Override (if needed beyond config) */
    @keyframes gradient-shift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }

    .stApp {
        background-color: #0F172A; /* Slate 900 */
        background-image: 
            radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
            radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
            radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
        background-size: 200% 200%;
        animation: gradient-shift 15s ease infinite;
        transition: background-image 0.5s ease;
    }

    /* Subtle change on hover */
    .stApp:hover {
        background-image: 
            radial-gradient(at 10% 10%, hsla(253,16%,10%,1) 0, transparent 50%), 
            radial-gradient(at 60% 10%, hsla(225,39%,35%,1) 0, transparent 50%), 
            radial-gradient(at 90% 10%, hsla(339,49%,35%,1) 0, transparent 50%);
    }

    /* Custom Header Styles */
    .header-container {
        padding: 0 0 1rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 2rem;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00B4D8 0%, #90E0EF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #94A3B8; /* Slate 400 */
        font-weight: 300;
        letter-spacing: 0.05em;
    }

    /* Card Styling */
    .glass-card {
        background: rgba(30, 41, 59, 0.7); /* Slate 800 with opacity */
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .glass-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 180, 216, 0.2);
        border-color: rgba(0, 180, 216, 0.5);
    }

    /* Metric Styling inside Cards */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    
    .metric-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #94A3B8;
        margin-bottom: 0.5rem;
    }

    /* Status Indicators */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    .status-ok { background: rgba(16, 185, 129, 0.1); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.2); }
    .status-err { background: rgba(239, 68, 68, 0.1); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.2); }
    .status-warn { background: rgba(245, 158, 11, 0.1); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.2); }

    /* Custom Button Overrides */
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
        height: auto; /* Allow height to adjust */
        padding: 0.8rem 2.5rem; /* Increased spacing */
        text-transform: uppercase;
        letter-spacing: 0.15em; /* Increased spacing */
        border: 1px solid rgba(255, 255, 255, 0.1); /* Subtle border */
        background-color: rgba(30, 41, 59, 0.5); /* Base color */
        color: #F8FAFC;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); /* Smoother transition */
        margin: 1rem 0; /* Add outer margin */
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 180, 216, 0.3), 0 4px 6px -2px rgba(0, 180, 216, 0.1);
        background-color: rgba(0, 180, 216, 0.2); /* Color change on hover */
        border-color: #00B4D8;
        color: #FFFFFF;
        letter-spacing: 0.2em; /* Expand text slightly on hover */
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        border-radius: 10% 10% 0% 0%;
        background-color: rgba(30, 41, 59, 0.5);
        color: #94A3B8;
        border: 1px solid transparent;        
    }
            
    .stTabs [data-baseweb="tab"] p {
        margin: 20px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(30, 41, 59, 0.8);
        color: #F8FAFC;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 180, 216, 0.1) !important;
        color: #00B4D8 !important;
        border: 1px solid rgba(0, 180, 216, 0.2) !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #020617; /* Very dark slate */
        border-right: 1px solid rgba(255,255,255, 0.05);
    }
    
    /* Code block styling */
    code {
        color: #F472B6;
        background: rgba(0,0,0,0.3);
    }

</style>
""", unsafe_allow_html=True)


def get_language_for_jurisdiction(code: Optional[str]) -> str:
    if not code:
        return "English"
    return JURISDICTION_LANGUAGE_MAP.get(code, "English")


def get_target_languages(jurisdictions: Optional[List[str]]) -> List[str]:
    if not jurisdictions:
        return []
    languages = {
        get_language_for_jurisdiction(code)
        for code in jurisdictions
        if get_language_for_jurisdiction(code) != "English"
    }
    return sorted(languages)


def get_active_english_keywords(kw_config: dict) -> tuple[List[str], List[str]]:
    english = kw_config.get("English", {})
    include_terms = normalize_terms(english.get("positive", []))
    exclude_terms = normalize_terms(english.get("negative", []))
    return include_terms, exclude_terms


def translation_context() -> str:
    return (
        "The keywords are for patent searches related to anomalous heat, "
        "low energy nuclear reactions (LENR), plasma discharge phenomena, "
        "transmutation, and excess energy claims. The terms appear in patent "
        "titles and abstracts and should be translated into technical, "
        "domain-appropriate language."
    )


def resolve_keywords_for_jurisdiction(
    include_terms: List[str],
    exclude_terms: List[str],
    jurisdiction_code: Optional[str],
    cache: dict,
    config,
) -> tuple[List[str], List[str], str, str]:
    language = get_language_for_jurisdiction(jurisdiction_code)
    if language == "English":
        return include_terms, exclude_terms, language, "english"

    set_id = keyword_set_id(include_terms, exclude_terms)
    cached = get_cached_translation(cache, set_id, language)
    if cached:
        return cached.get("include", include_terms), cached.get("exclude", exclude_terms), language, cached.get("source", "cache")

    if config.google_api_key:
        try:
            translated_include, translated_exclude = translate_keywords_with_llm(
                include_terms=include_terms,
                exclude_terms=exclude_terms,
                target_language=language,
                context=translation_context(),
                api_key=config.google_api_key,
            )
            set_cached_translation(
                cache,
                set_id=set_id,
                language=language,
                include_terms=translated_include,
                exclude_terms=translated_exclude,
                source="llm",
            )
            save_keyword_cache(cache)
            return translated_include, translated_exclude, language, "llm"
        except Exception:
            pass

    fallback = default_translation_for_language(language)
    if fallback:
        translated_include, translated_exclude = fallback
        set_cached_translation(
            cache,
            set_id=set_id,
            language=language,
            include_terms=translated_include,
            exclude_terms=translated_exclude,
            source="default",
        )
        save_keyword_cache(cache)
        return translated_include, translated_exclude, language, "default"

    return include_terms, exclude_terms, language, "fallback"


def load_keyword_set_callback(entry):
    """Callback to load keyword set into session state before widget rendering."""
    if 'keyword_config' in st.session_state:
        st.session_state['keyword_config'].setdefault("English", {})["positive"] = entry.get("include", [])
        st.session_state['keyword_config'].setdefault("English", {})["negative"] = entry.get("exclude", [])
    
    # Increment widget version to force recreation
    st.session_state['keyword_widget_version'] = st.session_state.get('keyword_widget_version', 0) + 1


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
    with st.sidebar:
        from project_aether.core.config import get_config
        config = get_config()
        
        # Use infinite date window (no date filtering)
        end_date = datetime.now()
        start_date = None
                     
        # Initialize language selection in session state
        if 'selected_language' not in st.session_state:
            st.session_state.selected_language = "English"
        
        language_options = list(LANGUAGE_MAP.keys())
        selected_language_name = st.selectbox(
            "Language",
            options=language_options,
            index=language_options.index(st.session_state.selected_language),
            help="Language for the search query. The API will use this language for multi-lingual search."
        )
        
        # Store selected language
        st.session_state.selected_language = selected_language_name
        selected_language_code = LANGUAGE_MAP[selected_language_name]
        
        # Jurisdiction is set to ALL by default (no filter)
        selected_jurisdictions = None

        keyword_config = st.session_state.get('keyword_config', DEFAULT_KEYWORDS)
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        cache = st.session_state.get('keyword_cache', {})
        widget_version = st.session_state.get('keyword_widget_version', 0)

        with st.expander("Current keyword set", expanded=True):
            set_label = st.text_input("Name (optional)", key="sidebar_set_label", placeholder="e.g. My Custom Keywords")

            include_text = st.text_area(
                "Include terms",
                value=", ".join(include_terms),
                height=120,
                key=f"sidebar_include_terms_{widget_version}",
            )
            exclude_text = st.text_area(
                "Exclude terms",
                value=", ".join(exclude_terms),
                height=120,
                key=f"sidebar_exclude_terms_{widget_version}",
            )

            updated_include = [term.strip() for term in include_text.split(",") if term.strip()]
            updated_exclude = [term.strip() for term in exclude_text.split(",") if term.strip()]
            keyword_config.setdefault("English", {})["positive"] = updated_include
            keyword_config.setdefault("English", {})["negative"] = updated_exclude
            st.session_state['keyword_config'] = keyword_config

            st.caption(f"Include: {len(updated_include)} terms | Exclude: {len(updated_exclude)} terms")

            if st.button("💾 Save", use_container_width=True):
                ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                save_keyword_cache(cache)
                st.session_state['keyword_cache'] = cache
                st.success("Keyword set saved to history")

        # Since jurisdiction is always ALL now, show translations for selected language if not English
        target_languages = [selected_language_name] if selected_language_name != "English" else []

        with st.expander("Translations", expanded=bool(target_languages)):
            if not target_languages:
                st.caption("No translations needed for English language selection.")
            else:
                if not config.google_api_key:
                    st.warning("LLM translation requires GOOGLE_API_KEY. Using cached or default translations only.")

                if st.button("Generate", use_container_width=True):
                    set_id = keyword_set_id(updated_include, updated_exclude)
                    for language in target_languages:
                        translation_successful = False
                        if config.google_api_key:
                            try:
                                translated_include, translated_exclude = translate_keywords_with_llm(
                                    include_terms=updated_include,
                                    exclude_terms=updated_exclude,
                                    target_language=language,
                                    context=translation_context(),
                                    api_key=config.google_api_key,
                                )
                                set_cached_translation(
                                    cache,
                                    set_id=set_id,
                                    language=language,
                                    include_terms=translated_include,
                                    exclude_terms=translated_exclude,
                                    source="llm",
                                )
                                translation_successful = True
                            except Exception as e:
                                st.warning(f"Translation failed for {language}: {e}")
                        
                        if not translation_successful:
                            fallback = default_translation_for_language(language)
                            if fallback:
                                translated_include, translated_exclude = fallback
                                set_cached_translation(
                                    cache,
                                    set_id=set_id,
                                    language=language,
                                    include_terms=translated_include,
                                    exclude_terms=translated_exclude,
                                    source="default",
                                )
                    save_keyword_cache(cache)
                    st.session_state['keyword_cache'] = cache
                    st.success("Translations updated")

                set_id = keyword_set_id(updated_include, updated_exclude)
                for language in target_languages:
                    cached = get_cached_translation(cache, set_id, language)
                    if cached:
                        include_list = ", ".join(cached.get("include", []))
                        exclude_list = ", ".join(cached.get("exclude", []))
                        st.markdown(f"**{language}**")
                        st.caption(f"Include: {include_list}")
                        st.caption(f"Exclude: {exclude_list}")
                    else:
                        st.markdown(f"**{language}**")
                        st.caption("No cached translation yet.")

        with st.expander("Previous keyword sets"):
            history_entries = get_history_entries(cache)
            if not history_entries:
                st.caption("No saved keyword sets yet.")
            else:
                labels = [entry.get("label", entry["id"]) for entry in history_entries]
                selected_label = st.selectbox("Select a saved set", options=labels)
                selected_entry = next(
                    (entry for entry in history_entries if entry.get("label", entry["id"]) == selected_label),
                    history_entries[0],
                )
                col_load, col_delete = st.columns(2)
                with col_load:
                    if st.button("📂", use_container_width=True, on_click=load_keyword_set_callback, args=(selected_entry,)):
                        st.success("Keyword set loaded")
                        time.sleep(0.3)
                        st.rerun()
                with col_delete:
                    if st.button("🗑️", use_container_width=True):
                        delete_keyword_set(cache, selected_entry["id"])
                        save_keyword_cache(cache)
                        st.session_state['keyword_cache'] = cache
                        st.success("Keyword set deleted")
                        time.sleep(0.5)
                        st.rerun()
        
        st.markdown("---")
        
        col_btn, _ = st.columns([1, 0.1])
        with col_btn:
            run_mission = st.button("🔍 Search", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # System Status in Sidebar
        st.write("#### Connectivity")
        
        if config.is_lens_configured:
            st.markdown('<div class="status-badge status-ok">Lens.org API Active</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-err">Lens.org API Offline</div>', unsafe_allow_html=True)
            st.caption("Missing `LENS_ORG_API_TOKEN`")
        
        st.write("") # Spacer
        
        if config.is_llm_configured:
            st.markdown('<div class="status-badge status-ok">LLM service connected</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-warn">LLM service offline</div>', unsafe_allow_html=True)

    # --- MAIN CONTENT TABS ---
    tab_dashboard, tab_results, tab_deepdive, tab_settings = st.tabs([
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
                run_patent_search(selected_language_code, start_date, end_date)
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
        st.markdown("### Search Results")
        
        assessments = st.session_state.get('assessments')
        if assessments:
            # Sort assessments by relevance_score descending
            sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)
            
            # Reverse mapping from code to jurisdiction name
            jurisdiction_code_to_name = {v: k for k, v in JURISDICTION_MAP.items()}
            # Special handling for WO jurisdiction
            jurisdiction_code_to_name["WO"] = "WO - PCT application"
            
            # Prepare data for dataframe
            data = []
            for a in sorted_assessments:
                # Convert jurisdiction code to name
                jurisdiction_name = jurisdiction_code_to_name.get(a.jurisdiction, a.jurisdiction)
                
                # Format title: capitalize first letter, rest lowercase
                formatted_title = a.title.capitalize() if a.title else ""
                
                # Format inventors: title case (each word starts with capital)
                formatted_inventors = ", ".join([inv.title() for inv in a.inventors]) if a.inventors else "Unknown"
                
                row = {
                    "Lens ID": a.lens_id,
                    "Patent #": a.doc_number,
                    "Title": formatted_title,
                    "Inventor(s)": formatted_inventors,
                    "Jurisdiction": jurisdiction_name,
                    "Score": f"{a.relevance_score:.1f}",
                    "Status": "Refused" if a.status_analysis.is_refused else "Withdrawn" if a.status_analysis.is_withdrawn else "Other",
                    "Reason": a.status_analysis.refusal_reason
                }
                data.append(row)
            
            # Create a dataframe and display it as read-only
            import pandas as pd
            df = pd.DataFrame(data)
            
            # Add CSS to disable text selection in dataframe
            st.markdown("""
            <style>
            [data-testid="stDataFrame"] {
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
            }
            [data-testid="stDataFrame"] * {
                user-select: none !important;
                -webkit-user-select: none !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Display dataframe with click handling
            event = st.dataframe(
                df, 
                use_container_width=True,
                selection_mode="single-row",
                hide_index=True,
                on_select="rerun",
                key="results_grid",
                column_config={
                    "Score": st.column_config.ProgressColumn(
                        "Relevance Score",
                        format="%s",
                        min_value=0,
                        max_value=100,
                    ),
                }
            )
            
            # Handle row selection for navigation to detailed analysis
            try:
                if event and isinstance(event, dict) and 'selection' in event and event['selection']:
                    selection = event['selection']
                    if 'rows' in selection and selection['rows'] and len(selection['rows']) > 0:
                        selected_row_index = selection['rows'][0]
                        selected_row = df.iloc[selected_row_index]
                        selected_lens_id = selected_row["Lens ID"]
                        
                        # Navigate to detailed analysis tab
                        st.session_state['selected_lens_id_for_analysis'] = selected_lens_id
            except (KeyError, IndexError, TypeError, AttributeError):
                # Silently ignore selection errors
                pass
        else:
            st.info("No results yet. Run an analysis to populate the table.")

    # --- DEEP DIVE TAB ---
    with tab_deepdive:
        st.markdown("### Detailed Analysis")
        assessments = st.session_state.get('assessments')
        
        if assessments:
            # Check if a specific lens ID was selected from the results tab
            selected_lens_id_from_results = st.session_state.get('selected_lens_id_for_analysis')
            
            # Determine which lens ID to display
            available_lens_ids = [a.lens_id for a in assessments]
            
            # If a lens ID was set from results tab selection, use it; otherwise use the first one
            if selected_lens_id_from_results and selected_lens_id_from_results in available_lens_ids:
                default_index = available_lens_ids.index(selected_lens_id_from_results)
                # Clear the session state after using it
                st.session_state['selected_lens_id_for_analysis'] = None
            else:
                default_index = 0
            
            # Selector
            selected_lens_id = st.selectbox(
                "Select Target for Analysis",
                options=available_lens_ids,
                index=default_index,
                format_func=lambda x: f"{x} - {next((a.title for a in assessments if a.lens_id == x), 'Unknown')}"
            )
            
            # Find selected assessment
            target = next((a for a in assessments if a.lens_id == selected_lens_id), None)
            
            if target:
                render_deep_dive(target)
        else:
            st.info("No analysis data available yet.")

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



def render_metric_card(label, value, subtext="", color="#00B4D8"):
    """Helper to render a custom HTML metric card"""
    st.markdown(f"""
    <div class="glass-card" style="border-left: 4px solid {color};">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">{subtext}</div>
    </div>
    """, unsafe_allow_html=True)

def show_placeholder_dashboard():
    """Display modern placeholder dashboard."""
    
    st.markdown("### Search Status: Idle")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("Total Results", "—", "Awaiting search", "#94A3B8")
    with col2:
        render_metric_card("High Value", "—", "Substantive Rejections", "#EF4444")
    with col3:
        render_metric_card("Medium Value", "—", "Potential Interest", "#F59E0B")
    with col4:
        render_metric_card("Low Value", "—", "Probable Noise", "#00B4D8")

    
def render_dashboard_metrics(dashboard):
    """Render the dashboard with actual data."""
    st.markdown(f"### Search Status: Completed (Ref: {dashboard.mission_id})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("Total Results", dashboard.total_patents_searched, "Patents Scanned", "#94A3B8")
    with col2:
        render_metric_card("High Value", dashboard.high_priority_count, "Critical Findings", "#EF4444")
    with col3:
        render_metric_card("Medium Value", dashboard.medium_priority_count, "Potential Interest", "#F59E0B")
    with col4:
        render_metric_card("Low Value", dashboard.anomalous_count, "Probable Noise", "#00B4D8")
        
def render_deep_dive(assessment):
    """Render a detailed view of a patent assessment."""
    
    # Header logic
    color = "#94A3B8"
    if assessment.intelligence_value == "HIGH": color = "#EF4444"
    elif assessment.intelligence_value == "MEDIUM": color = "#F59E0B"
    
    # Generate Lens.org link
    lens_url = f"https://www.lens.org/lens/patent/{assessment.lens_id}/frontpage"
    
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid {color}">
        <h2>{assessment.title}</h2>
        <p style="font-family: monospace; color: {color}; font-size: 1.2rem;">
            {assessment.lens_id} | {assessment.jurisdiction} | {assessment.doc_number}
        </p>
        <p style="margin-top: 10px;">
            <a href="{lens_url}" target="_blank" style="color: #00B4D8; text-decoration: none;">
                🔗 View on Lens.org
            </a>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Abstract")
        patent_data = next((p for p in st.session_state.get('all_raw_results', []) if p.get('lens_id') == assessment.lens_id), {})
        
        # Handle abstract with multiple languages
        abstract_data = patent_data.get('abstract', None)
        
        if abstract_data:
            # If abstract is a list of language objects
            if isinstance(abstract_data, list):
                lang_map = {
                    'en': 'English',
                    'fr': 'French',
                    'de': 'German',
                    'es': 'Spanish',
                    'it': 'Italian',
                    'pt': 'Portuguese',
                    'ru': 'Russian',
                    'zh': 'Chinese',
                    'ja': 'Japanese',
                    'ko': 'Korean',
                    'hu': 'Hungarian',
                    'ar': 'Arabic',
                }
                
                # Build dictionary of available languages
                available_abstracts = {}
                for abstract_obj in abstract_data:
                    lang_code = abstract_obj.get('lang', 'unknown').lower()
                    lang_name = lang_map.get(lang_code, lang_code.upper())
                    available_abstracts[lang_name] = abstract_obj.get('text', '')
                
                # List of preferred languages to show
                preferred_langs = ['English', 'Hungarian', 'French', 'German', 'Spanish', 'Chinese', 'Russian']
                
                # Create tabs for available languages
                tab_labels = []
                tab_contents = []
                
                for lang in preferred_langs:
                    if lang in available_abstracts:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])
                
                # Add any other languages not in the preferred list
                for lang in sorted(available_abstracts.keys()):
                    if lang not in preferred_langs:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])
                
                # Create tabs for available languages
                if tab_labels:
                    tabs = st.tabs(tab_labels)
                    for tab, content in zip(tabs, tab_contents):
                        with tab:
                            st.info(content)
                else:
                    st.info('No abstract available')
            else:
                # If abstract is a simple string
                st.info(abstract_data)
        else:
            st.info('No abstract available')
        
        st.markdown("#### Legal Status Review")
        st.write(f"**Interpretation:** {assessment.status_analysis.interpretation}")
        st.write(f"**Refusal Reason:** {assessment.status_analysis.refusal_reason}")
    
    with col2:
        # Relevance section with tooltip
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px;">
            <h4 style="margin: 0;">AI Analysis</h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Relevance score with icon and tooltip
        relevance_tooltip = "Relevance score indicates how closely this patent matches the search criteria. Based on keyword matching in title, abstract, and claims, combined with context analysis."
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 15px; margin-bottom: 10px;">
            <strong>Relevance</strong>
            <span style="cursor: help; color: #94A3B8;" title="{relevance_tooltip}">?</span>
        </div>
        """, unsafe_allow_html=True)
        st.progress(assessment.relevance_score / 100, text=f"{assessment.relevance_score:.1f}%")
        
        # Tags section with icon and tooltip
        tags_tooltip = "Classification tags identify key technical domains and subject areas covered by the patent. These help categorize and filter related technologies."
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px; margin-bottom: 5px;">
            <strong>Tags</strong>
            <span style="cursor: help; color: #94A3B8;" title="{tags_tooltip}">?</span>
        </div>
        """, unsafe_allow_html=True)
        if assessment.classification_tags:
            for tag in assessment.classification_tags:
                st.markdown(f"`{tag}`")
        else:
            st.caption("No specific tags")
            
        # Notable Features section with icon and tooltip
        features_tooltip = "Notable features highlight unusual or significant technical characteristics detected in the patent, such as anomalous energy patterns or heat signatures."
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px; margin-bottom: 5px;">
            <strong>Notable Features</strong>
            <span style="cursor: help; color: #94A3B8;" title="{features_tooltip}">?</span>
        </div>
        """, unsafe_allow_html=True)
        if assessment.is_anomalous:
            st.markdown("`Heat signature detected`")
        else:
            st.caption("None detected")


def run_patent_search(language_code, start_date, end_date):
    """Execute the patent search with specified language."""
    
    status_container = st.empty()
    progress_bar = st.progress(0)
    
    try:
        from project_aether.tools.lens_api import LensConnector
        from project_aether.agents.analyst import AnalystAgent
        from project_aether.utils.artifacts import ArtifactGenerator
        from project_aether.core.config import get_config
        from project_aether.core.keyword_translation import (
            keyword_set_id,
            get_cached_translation,
        )
        
        status_container.info("Initializing analysis parameters...")
        time.sleep(1)  # UX pacing
        
        config = get_config()
        connector = LensConnector()
        keyword_config = st.session_state.get('keyword_config', DEFAULT_KEYWORDS)
        cache = st.session_state.get('keyword_cache', load_keyword_cache())
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        ensure_keyword_set(cache, include_terms, exclude_terms)
        save_keyword_cache(cache)
        st.session_state['keyword_cache'] = cache
        analyst = AnalystAgent(keyword_config=keyword_config)
        generator = ArtifactGenerator()
        
        # Determine which keywords to use based on language
        search_language_name = None
        for display_name, code in LANGUAGE_MAP.items():
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
                status_container.info(f"Using cached translations for {search_language_name}")
        
        all_results = []
        
        total_steps = 3  # init + search + analysis + generation
        current_step = 1
        progress_bar.progress(33)
        
        status_container.markdown(f"Searching with language code {language_code}...")
        
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
        except Exception as e:
            logger.error(f"Search failed: {e}")
            st.error(f"Search failed: {e}")
        
        st.session_state['all_raw_results'] = all_results

        current_step += 1
        progress_bar.progress(int((current_step / total_steps) * 100))
        status_container.markdown(f"Analyzing {len(all_results)} candidates for key signals...")
        
        assessments = analyst.analyze_batch(all_results)
        
        current_step += 1
        progress_bar.progress(100)
        status_container.markdown("Compiling dashboard outputs...")
        
        dashboard = generator.create_dashboard_artifact(
            assessments=[a.to_dict() for a in assessments],
            jurisdictions=["ALL"]
        )
        
        st.session_state['assessments'] = assessments
        st.session_state['dashboard'] = dashboard
        
        status_container.success("Analysis complete. Dashboard updated.")
        time.sleep(2)
        status_container.empty()
        st.rerun()

    except ImportError as e:
        st.error(f"System Error: Dependency missing ({e}). Run `uv sync`.")
    except Exception as e:
        st.error(f"Analysis failed: {e}")
        logger.error(f"Analysis failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()
