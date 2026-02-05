import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
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
""",
        unsafe_allow_html=True,
    )
