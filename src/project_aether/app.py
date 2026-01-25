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
from project_aether.core.keywords import DEFAULT_KEYWORDS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ProjectAether")

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
    "Finland": "FI"
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
        padding: 2rem 0 1rem 0;
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
        border-radius: 8px;
        background-color: rgba(30, 41, 59, 0.5);
        color: #94A3B8;
        border: 1px solid transparent;        
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

def main():
    """Main application entry point."""
    
    # Initialize Session State for Keywords if not present
    if 'keyword_config' not in st.session_state:
        st.session_state['keyword_config'] = copy.deepcopy(DEFAULT_KEYWORDS)
    
    # --- HEADER SECTION ---
    st.markdown("""
    <div class="header-container">
        <div class="main-title">Project Aether</div>
        <div class="subtitle">Patent intelligence and analysis</div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- SIDEBAR CONFIGURATION ---
    with st.sidebar:
        st.markdown(
            "<h2 style='text-align: center; color: #00B4D8;'>Filters</h2>",
            unsafe_allow_html=True
        )
        st.markdown("---")
        
        st.write("#### Temporal Scope")
        
        # Date range selection
        end_date = st.date_input(
            "Target End Date",
            value=datetime.now(),
            help="Analysis will run up to this date"
        )
        
        years_back = st.slider(
            "Lookback Window (Years)",
            min_value=0,
            max_value=50,
            value=0,
            help="Historical depth of the search. Set to 0 for infinite (no date filter)"
        )
        
        if years_back == 0:
            start_date = None
            st.caption(f"Window: `Infinite (No Date Filter)` to `{end_date}`")
        else:
            start_date = end_date - timedelta(days=years_back * 365)
            st.caption(f"Window: `{start_date}` to `{end_date}`")
        
        st.markdown("---")
        
        st.write("#### Geographic Scope")
        
        # List of jurisdiction display names
        jurisdiction_display_names = [
            "All",
            "European Patents",
            "China",
            "Japan",
            "United States",
            "Germany",
            "Republic of Korea",
            "United Kingdom",
            "France",
            "Canada",
            "Russia",
            "Poland",
            "Romania",
            "Czech Republic",
            "Netherlands",
            "Spain",
            "Italy",
            "Sweden",
            "Norway",
            "Finland"
        ]
        
        # Initialize previous selection in session state
        if 'prev_jurisdiction_selection' not in st.session_state:
            st.session_state.prev_jurisdiction_selection = ["All"]
        
        selected_jurisdiction_names = st.multiselect(
            "Target Jurisdictions",
            options=jurisdiction_display_names,
            default=st.session_state.prev_jurisdiction_selection,
            help="Multinational patent offices to surveil. Select 'All' for no jurisdiction filter."
        )
        
        # Handle "All" selection logic
        prev_selection = st.session_state.prev_jurisdiction_selection
        
        # If "All" was just selected (wasn't in previous but is now)
        if "All" in selected_jurisdiction_names and "All" not in prev_selection:
            selected_jurisdiction_names = ["All"]
        # If other jurisdictions were selected while "All" was already selected
        elif "All" in prev_selection and len(selected_jurisdiction_names) > 1 and "All" in selected_jurisdiction_names:
            # Remove "All" from selection
            selected_jurisdiction_names = [name for name in selected_jurisdiction_names if name != "All"]
        
        # Update session state
        st.session_state.prev_jurisdiction_selection = selected_jurisdiction_names
        
        # Convert display names to ISO codes or None for "All"
        if "All" in selected_jurisdiction_names:
            # "All" means no jurisdiction filter - pass None or empty list
            selected_jurisdictions = None  # Will be handled to skip jurisdiction filtering
        else:
            selected_jurisdictions = [JURISDICTION_MAP[name] for name in selected_jurisdiction_names]
        
        st.markdown("---")
        
        col_btn, _ = st.columns([1, 0.1])
        with col_btn:
            run_mission = st.button("Run Analysis", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # System Status in Sidebar
        st.write("#### Connectivity")
        
        from project_aether.core.config import get_config
        config = get_config()
        
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
    tab_dashboard, tab_matrix, tab_deepdive, tab_settings = st.tabs([
        "Dashboard",
        "Rejection Matrix",
        "Detailed Analysis",
        "Settings"
    ])
    
    # --- DASHBOARD TAB ---
    with tab_dashboard:
        if run_mission:
            # Check if jurisdictions are selected (None is valid for "All", but empty selection is not)
            if not selected_jurisdiction_names:
                st.error("Analysis aborted: no jurisdictions selected")
            elif not config.is_lens_configured:
                st.error("Analysis aborted: Lens.org API disconnected")
            else:
                run_patent_search(selected_jurisdictions, start_date, end_date)
        else:
            dashboard_state = st.session_state.get('dashboard')
            if dashboard_state:
                # Render existing dashboard data
                render_dashboard_metrics(dashboard_state)
            else:
                # Show placeholder dashboard
                show_placeholder_dashboard()
    
    # --- MATRIX TAB ---
    with tab_matrix:
        st.markdown("### Rejection Matrix")
        
        assessments = st.session_state.get('assessments')
        if assessments:
            # Sort assessments by relevance_score descending
            sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)
            
            # Prepare data for dataframe
            data = []
            for a in sorted_assessments:
                row = {
                    "Lens ID": a.lens_id,
                    "Patent #": a.doc_number,
                    "Title": a.title,
                    "Inventor(s)": ", ".join(a.inventors) if a.inventors else "Unknown",
                    "Jurisdiction": a.jurisdiction,
                    "Intelligence": a.intelligence_value,
                    "Score": f"{a.relevance_score:.1f}",
                    "Status": "Refused" if a.status_analysis.is_refused else "Withdrawn" if a.status_analysis.is_withdrawn else "Other",
                    "Reason": a.status_analysis.refusal_reason
                }
                data.append(row)
            
            st.dataframe(
                data, 
                use_container_width=True,
                column_config={
                    "Intelligence": st.column_config.TextColumn(
                        "Intelligence",
                        help="Calculated Intelligence Value",
                        validate="^(HIGH|MEDIUM|LOW)$"
                    ),
                    "Score": st.column_config.ProgressColumn(
                        "Relevance Score",
                        format="%s",
                        min_value=0,
                        max_value=100,
                    ),
                }
            )
        else:
            st.info("No results yet. Run an analysis to populate the matrix.")

    # --- DEEP DIVE TAB ---
    with tab_deepdive:
        st.markdown("### Detailed Analysis")
        assessments = st.session_state.get('assessments')
        
        if assessments:
            # Selector
            selected_lens_id = st.selectbox(
                "Select Target for Analysis",
                options=[a.lens_id for a in assessments],
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
    
    st.markdown("### Status: Idle")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("Total Targets", "—", "Awaiting search", "#94A3B8")
    with col2:
        render_metric_card("High Value", "—", "Substantive Rejections", "#EF4444")
    with col3:
        render_metric_card("Medium Value", "—", "Withdrawn / Anomalous", "#F59E0B")
    with col4:
        render_metric_card("Signal Anomalies", "—", "Plasma indicators", "#00B4D8")
    
    st.markdown("---")
    
    # Empty State Hero
    st.markdown("""
    <div style="text-align: center; padding: 4rem 2rem; background: rgba(255,255,255,0.02); border-radius: 16px;">
        <h2 style="color: #94A3B8;">Ready to start analysis</h2>
        <p style="color: #64748b; max-width: 600px; margin: 0 auto 2rem auto;">
            Ready to query multiple jurisdictions for rejected patent applications
            that match the selected criteria.
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard_metrics(dashboard):
    """Render the dashboard with actual data."""
    st.markdown(f"### Analysis Status: Completed (Ref: {dashboard.mission_id})")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("Total Targets", dashboard.total_patents_searched, "Patents Scanned", "#94A3B8")
    with col2:
        render_metric_card("High Value", dashboard.high_priority_count, "Critical Findings", "#EF4444")
    with col3:
        render_metric_card("Medium Value", dashboard.medium_priority_count, "Potential Interest", "#F59E0B")
    with col4:
        render_metric_card("Signal Anomalies", dashboard.anomalous_count, "Plasma indicators", "#00B4D8")
        
    st.markdown("### Top Jurisdictions")
    # Simple bar chart using st.bar_chart if we had the breakdown, for now just text
    if dashboard.top_jurisdiction:
        st.info(f"Most activity detected in: **{dashboard.top_jurisdiction}**")

def render_deep_dive(assessment):
    """Render a detailed view of a patent assessment."""
    
    # Header logic
    color = "#94A3B8"
    if assessment.intelligence_value == "HIGH": color = "#EF4444"
    elif assessment.intelligence_value == "MEDIUM": color = "#F59E0B"
    
    st.markdown(f"""
    <div class="glass-card" style="border-top: 4px solid {color}">
        <h2>{assessment.title}</h2>
        <p style="font-family: monospace; color: {color}; font-size: 1.2rem;">
            {assessment.lens_id} | {assessment.jurisdiction} | {assessment.doc_number}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### Abstract")
        patent_data = next((p for p in st.session_state.get('all_raw_results', []) if p.get('lens_id') == assessment.lens_id), {})
        abstract_text = patent_data.get('abstract', 'No abstract available')
        st.info(abstract_text)
        
        st.markdown("#### Legal Status Review")
        st.write(f"**Interpretation:** {assessment.status_analysis.interpretation}")
        st.write(f"**Refusal Reason:** {assessment.status_analysis.refusal_reason}")
    
    with col2:
        st.markdown("#### AI Analysis")
        st.progress(assessment.relevance_score / 100, text=f"Relevance: {assessment.relevance_score:.1f}%")
        
        st.markdown("**Tags:**")
        if assessment.classification_tags:
            for tag in assessment.classification_tags:
                st.markdown(f"`{tag}`")
        else:
            st.caption("No specific tags")
            
        st.markdown("**Notable Features:**")
        if assessment.is_anomalous:
            st.markdown("`Heat signature detected`")
        else:
            st.caption("None detected")


def run_patent_search(jurisdictions, start_date, end_date):
    """Execute the patent search."""
    
    status_container = st.empty()
    progress_bar = st.progress(0)
    
    try:
        from project_aether.tools.lens_api import LensConnector
        from project_aether.agents.analyst import AnalystAgent
        from project_aether.utils.artifacts import ArtifactGenerator
        
        status_container.info("Initializing analysis parameters...")
        time.sleep(1)  # UX pacing
        
        connector = LensConnector()
        keyword_config = st.session_state.get('keyword_config', DEFAULT_KEYWORDS)
        analyst = AnalystAgent(keyword_config=keyword_config)
        generator = ArtifactGenerator()
        
        all_results = []
        
        if jurisdictions is None:
            total_steps = 3  # init + search + analysis + generation
            current_step = 1
            progress_bar.progress(33)
            
            status_container.markdown("Searching all jurisdictions (no filter)...")
            
            try:
                result = asyncio.run(
                    connector.search_by_jurisdiction(
                        jurisdiction=None,
                        start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                )
                patents = result.get("data", [])
                all_results.extend(patents)
            except Exception as e:
                logger.error(f"Search failed for all jurisdictions: {e}")
                st.error(f"Search failed: {e}")
        else:
            total_steps = len(jurisdictions) + 2  # +2 for analysis and generation
            current_step = 0
            
            for juris in jurisdictions:
                current_step += 1
                progress = int((current_step / total_steps) * 100)
                progress_bar.progress(progress)
                
                status_container.markdown(f"Searching jurisdiction {juris}...")
                
                try:
                    result = asyncio.run(
                        connector.search_by_jurisdiction(
                            jurisdiction=juris,
                            start_date=start_date.strftime("%Y-%m-%d") if start_date else None,
                            end_date=end_date.strftime("%Y-%m-%d"),
                        )
                    )
                    patents = result.get("data", [])
                    all_results.extend(patents)
                except Exception as e:
                    logger.error(f"Search failed for {juris}: {e}")
        
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
            jurisdictions=jurisdictions if jurisdictions else ["ALL"]
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
