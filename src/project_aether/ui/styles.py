import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Full-width responsive main container */
    .stMainBlockContainer, .block-container {
        max-width: 1440px !important;
        padding-top: 1.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-bottom: 2.5rem !important;
    }

    .stApp {
        background-color: #0F172A;
        background-image:
            radial-gradient(at 0% 0%, hsla(253, 16%, 7%, 1) 0, transparent 50%),
            radial-gradient(at 50% 0%, hsla(225, 39%, 24%, 1) 0, transparent 50%),
            radial-gradient(at 100% 0%, hsla(200, 45%, 18%, 1) 0, transparent 50%);
    }

    /* Header */
    .header-container {
        padding: 0 0 0.75rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1.25rem;
    }

    .main-title {
        font-size: 2.25rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00B4D8 0%, #90E0EF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
        margin-bottom: 0.25rem;
    }

    .subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        font-weight: 400;
        letter-spacing: 0.03em;
    }

    /* Glass Cards (inset accent avoids corner tapering/hooks) */
    .glass-card {
        background: rgba(30, 41, 59, 0.75);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.15rem 1.35rem;
        margin-bottom: 0.85rem;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .glass-card:hover {
        border-color: rgba(0, 180, 216, 0.45);
        box-shadow: 0 8px 24px -6px rgba(0, 0, 0, 0.45);
    }

    .metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #F8FAFC;
        line-height: 1.15;
    }

    .metric-subtext {
        color: #94A3B8;
        font-size: 0.8rem;
        margin-top: 0.35rem;
    }

    /* Readable dark abstract container */
    .abstract-box {
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 8px;
        padding: 1rem 1.25rem;
        color: #E2E8F0;
        font-size: 0.94rem;
        line-height: 1.65;
        margin-bottom: 0.75rem;
    }

    /* Inline tag pills that never split mid-tag */
    .tag-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin: 0.35rem 0 0.75rem 0;
    }

    .tag-pill {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 500;
        color: #E2E8F0;
        background: rgba(0, 180, 216, 0.14);
        border: 1px solid rgba(0, 180, 216, 0.3);
        white-space: nowrap;
    }

    /* Status Badges */
    .status-badge {
        display: block;
        width: fit-content;
        padding: 0.28rem 0.75rem;
        margin-bottom: 0.45rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 600;
    }

    .status-ok { background: rgba(16, 185, 129, 0.12); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.28); }
    .status-err { background: rgba(239, 68, 68, 0.12); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.28); }
    .status-warn { background: rgba(245, 158, 11, 0.12); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.28); }

    /* Unified compact Button & Download Button styling */
    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 8px;
        font-size: 0.875rem;
        font-weight: 600;
        padding: 0.45rem 0.95rem;
        min-height: 2.4rem;
        margin: 0;
        text-transform: none;
        letter-spacing: 0.01em;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background-color: rgba(30, 41, 59, 0.7);
        color: #F8FAFC;
        transition: all 0.2s ease;
        white-space: nowrap;
    }

    div.stButton > button[kind="primary"] {
        background-color: #0096C7;
        border-color: #00B4D8;
        color: #FFFFFF;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: #00B4D8;
        border-color: #90E0EF;
        color: #FFFFFF;
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        border-color: #00B4D8;
        background-color: rgba(0, 180, 216, 0.18);
        color: #FFFFFF;
    }

    /* Tabs: crisp hierarchy (active = bright white + cyan accent, inactive = muted slate) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        margin-bottom: 1rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 2.6rem;
        padding: 0 1rem;
        border-radius: 8px 8px 0 0;
        background-color: transparent;
        color: #94A3B8 !important;
        border: 1px solid transparent;
        font-weight: 500;
    }

    .stTabs [data-baseweb="tab"] p {
        margin: 0;
        font-size: 0.92rem;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(30, 41, 59, 0.65);
        color: #E2E8F0 !important;
    }

    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 180, 216, 0.14) !important;
        color: #FFFFFF !important;
        font-weight: 600;
        border: 1px solid rgba(0, 180, 216, 0.35) !important;
        border-bottom: 2px solid #00B4D8 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #020617;
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* Inline code */
    code {
        color: #7DD3FC;
        background: rgba(15, 23, 42, 0.6);
        padding: 0.12rem 0.35rem;
        border-radius: 4px;
        font-size: 0.85em;
    }
</style>
""",
        unsafe_allow_html=True,
    )
