"""
Project Aether - Agentic Patent Intelligence Framework
Main Streamlit application entry point.
"""

import streamlit as st
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ProjectAether")

# Page configuration
st.set_page_config(
    page_title="Project Aether - Mission Control",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1e3a8a;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
    }
    .alert-high {
        background-color: #fee2e2;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #dc2626;
    }
    .alert-medium {
        background-color: #fef3c7;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #f59e0b;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point."""
    
    # Header
    st.markdown('<div class="main-header">🔭 Project Aether</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Agentic Patent Intelligence Framework</div>',
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # Sidebar - Mission Control
    with st.sidebar:
        st.header("🕵️ Mission Control")
        
        st.subheader("Configuration")
        
        # Date range selection
        end_date = st.date_input(
            "End Date",
            value=datetime.now(),
            help="Search up to this date"
        )
        
        days_back = st.slider(
            "Days Back",
            min_value=1,
            max_value=30,
            value=7,
            help="Number of days to search backwards"
        )
        
        start_date = end_date - timedelta(days=days_back)
        st.info(f"Search window: {start_date} to {end_date}")
        
        # Jurisdiction selection
        st.subheader("Target Jurisdictions")
        
        all_jurisdictions = ["RU", "PL", "RO", "CZ", "NL", "ES", "IT", "SE", "NO", "FI"]
        
        selected_jurisdictions = st.multiselect(
            "Select jurisdictions",
            options=all_jurisdictions,
            default=["RU", "PL"],
            help="Countries to search for patent activity"
        )
        
        st.markdown("---")
        
        # Mission trigger
        run_mission = st.button("🚀 Launch Mission", type="primary", use_container_width=True)
        
        st.markdown("---")
        
        # Status
        st.subheader("System Status")
        
        from project_aether.core.config import get_config
        
        config = get_config()
        
        if config.is_lens_configured:
            st.success("✅ Lens.org API configured")
        else:
            st.error("❌ Lens.org API not configured")
            st.info("Add LENS_ORG_API_TOKEN to your .env file")
        
        if config.is_llm_configured:
            st.success("✅ LLM API configured")
        else:
            st.warning("⚠️ LLM API not configured")
    
    # Main content area
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "📋 Review Matrix",
        "🔬 Deep Dive",
        "⚙️ Settings"
    ])
    
    with tab1:
        st.header("Mission Dashboard")
        
        if run_mission:
            if not selected_jurisdictions:
                st.error("⚠️ Please select at least one jurisdiction")
            elif not config.is_lens_configured:
                st.error("⚠️ Lens.org API is not configured. Cannot run mission.")
            else:
                run_patent_search(selected_jurisdictions, start_date, end_date)
        else:
            # Show placeholder dashboard
            show_placeholder_dashboard()
    
    with tab2:
        st.header("Patent Review Matrix")
        st.info("📋 Patent results will appear here after running a mission")
        
        # Placeholder table
        st.markdown("""
        The review matrix displays all discovered patents with:
        - Intelligence value (HIGH/MEDIUM/LOW)
        - Legal status (Refused/Withdrawn/Lapsed)
        - Relevance score
        - Jurisdiction
        - Interactive filtering and sorting
        """)
    
    with tab3:
        st.header("Deep Dive Analysis")
        st.info("🔬 Select a patent from the Review Matrix to see detailed analysis")
        
        st.markdown("""
        Deep dive includes:
        - Full abstract and claims
        - INPADOC status code analysis
        - Applicant and inventor information
        - Classification codes (IPC/CPC)
        - Related patents
        - Timeline visualization
        """)
    
    with tab4:
        st.header("Settings")
        
        st.subheader("API Configuration")
        st.info(
            "Configure API keys in the `.env` file in the project root. "
            "See `.env.example` for the required variables."
        )
        
        st.subheader("Search Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.number_input(
                "Max results per jurisdiction",
                min_value=10,
                max_value=200,
                value=50,
                help="Maximum number of patents to retrieve"
            )
        
        with col2:
            st.number_input(
                "Relevance threshold",
                min_value=0,
                max_value=100,
                value=40,
                help="Minimum relevance score to display"
            )
        
        st.subheader("About")
        st.markdown("""
        **Project Aether** is an agentic patent intelligence framework designed to monitor
        anomalous hydrogen phenomena patents in Russia and strategic European corridors.
        
        - **License:** AGPLv3
        - **Version:** 0.1.0
        - **Stack:** Python 3.12+ | uv | Streamlit | LangChain
        
        Built with skepticism and curiosity. 🔭
        """)


def show_placeholder_dashboard():
    """Display placeholder dashboard metrics."""
    st.subheader("📊 Mission Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Patents",
            "—",
            help="Total patents discovered"
        )
    
    with col2:
        st.metric(
            "🚨 High Priority",
            "—",
            help="Substantive rejections"
        )
    
    with col3:
        st.metric(
            "⚠️ Medium Priority",
            "—",
            help="Withdrawn applications"
        )
    
    with col4:
        st.metric(
            "Anomalous",
            "—",
            help="Contains anomalous terminology"
        )
    
    st.markdown("---")
    
    st.info(
        "👈 Configure your mission parameters in the sidebar and click "
        "**🚀 Launch Mission** to begin the patent search."
    )
    
    st.markdown("""
    ### The Agentic Workflow
    
    1. **Manager Agent** orchestrates the weekly mission
    2. **Researcher Agent** queries Lens.org for discontinued/withdrawn patents
    3. **Analyst Agent** performs forensic analysis of legal status codes
    4. **Artifacts** are generated for human review
    
    This tool focuses on the "negative space" of innovation—rejected patents that
    may contain valuable intelligence about anomalous hydrogen phenomena.
    """)


def run_patent_search(jurisdictions, start_date, end_date):
    """
    Execute the patent search mission.
    
    Args:
        jurisdictions: List of jurisdiction codes
        start_date: Start date for search
        end_date: End date for search
    """
    st.subheader("🚀 Mission in Progress")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        import asyncio
        from project_aether.tools.lens_api import LensConnector
        from project_aether.agents.analyst import AnalystAgent
        from project_aether.utils.artifacts import ArtifactGenerator
        
        # Initialize components
        status_text.text("Initializing mission components...")
        progress_bar.progress(10)
        
        connector = LensConnector()
        analyst = AnalystAgent()
        generator = ArtifactGenerator()
        
        # Search each jurisdiction
        all_results = []
        total_jurisdictions = len(jurisdictions)
        
        for idx, jurisdiction in enumerate(jurisdictions):
            status_text.text(f"Searching {jurisdiction}... ({idx + 1}/{total_jurisdictions})")
            progress = 10 + (idx * 30 // total_jurisdictions)
            progress_bar.progress(progress)
            
            # Run async search
            try:
                result = asyncio.run(
                    connector.search_by_jurisdiction(
                        jurisdiction=jurisdiction,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d"),
                    )
                )
                
                patents = result.get("data", [])
                all_results.extend(patents)
                
                st.success(f"✅ {jurisdiction}: Found {len(patents)} patents")
                
            except Exception as e:
                st.error(f"❌ {jurisdiction}: {str(e)}")
                logger.error(f"Search failed for {jurisdiction}: {e}")
        
        # Analyze results
        status_text.text("Analyzing patents...")
        progress_bar.progress(50)
        
        assessments = analyst.analyze_batch(all_results)
        
        # Generate artifacts
        status_text.text("Generating artifacts...")
        progress_bar.progress(80)
        
        dashboard = generator.create_dashboard_artifact(
            assessments=[a.to_dict() for a in assessments],
            jurisdictions=jurisdictions
        )
        
        # Display results
        progress_bar.progress(100)
        status_text.text("✅ Mission complete!")
        
        st.success(f"🎯 Mission {dashboard.mission_id} completed successfully!")
        
        # Display dashboard
        st.markdown("---")
        st.subheader("📊 Mission Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Patents",
                dashboard.total_patents_searched
            )
        
        with col2:
            st.metric(
                "🚨 High Priority",
                dashboard.high_priority_count
            )
        
        with col3:
            st.metric(
                "⚠️ Medium Priority",
                dashboard.medium_priority_count
            )
        
        with col4:
            st.metric(
                "⚡ Anomalous",
                dashboard.anomalous_count
            )
        
        # Show high priority findings
        if dashboard.high_priority_count > 0:
            st.markdown("---")
            st.subheader("🚨 High Priority Findings")
            
            high_priority = [a for a in assessments if a.intelligence_value == "HIGH"]
            
            for assessment in high_priority[:5]:  # Show top 5
                with st.expander(
                    f"**{assessment.lens_id}** - {assessment.title} ({assessment.jurisdiction})"
                ):
                    st.markdown(f"**Relevance Score:** {assessment.relevance_score:.1f}/100")
                    st.markdown(f"**Status:** {assessment.status_analysis.interpretation}")
                    st.markdown(f"**Summary:** {assessment.summary}")
        
        # Store results in session state for other tabs
        st.session_state['assessments'] = assessments
        st.session_state['dashboard'] = dashboard
        
    except ImportError as e:
        st.error(f"❌ Import error: {e}")
        st.info("Make sure all dependencies are installed: `uv sync`")
    except Exception as e:
        st.error(f"❌ Mission failed: {e}")
        logger.error(f"Mission failed: {e}", exc_info=True)
        progress_bar.empty()
        status_text.empty()


if __name__ == "__main__":
    main()
