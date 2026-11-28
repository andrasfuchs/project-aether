import streamlit as st


def inject_global_styles() -> None:
    st.markdown(
        """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

    :root {
        --bg-canvas: #F7F8FA;
        --bg-surface: #FFFFFF;
        --bg-subtle: #F1F4F8;
        --bg-hover: #EEF2F6;
        --border-hairline: #E2E6ED;
        --border-strong: #CBD5E1;

        --text-primary: #0F172A;
        --text-secondary: #475569;
        --text-muted: #5B6678;

        --accent: #2563EB;
        --accent-hover: #1D4ED8;
        --accent-soft: rgba(37, 99, 235, 0.08);

        --signal-high: #DC2626;
        --signal-medium: #D97706;
        --signal-low: #475569;
        --signal-ok: #059669;

        --font-sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;

        --text-heading: 1.25rem;
        --text-body: 0.9375rem;
        --text-sm: 0.8125rem;

        --radius-sm: 6px;
        --radius-md: 8px;
        --ease-out: cubic-bezier(0.22, 1, 0.36, 1);
    }

    html, body, [class*="css"], .stApp, button, input, textarea, select {
        font-family: var(--font-sans) !important;
        color: var(--text-primary);
    }

    code, pre, .aether-mono {
        font-family: var(--font-mono) !important;
    }

    /* Clean architectural canvas */
    .stApp {
        background-color: var(--bg-canvas);
    }

    /* Subtle top chrome */
    [data-testid="stDecoration"] {
        display: none;
    }

    header[data-testid="stHeader"] {
        background: rgba(247, 248, 250, 0.88);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border-bottom: 1px solid transparent;
    }

    /* Main workspace container */
    .stMainBlockContainer, .block-container {
        max-width: 1380px !important;
        padding-top: 2.75rem !important;
        padding-left: 2.25rem !important;
        padding-right: 2.25rem !important;
        padding-bottom: 3rem !important;
    }

    @media (max-width: 768px) {
        .stMainBlockContainer, .block-container {
            padding-top: 2.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* Typography discipline: 3 body sizes */
    .stMarkdown p, .stMarkdown li {
        font-size: var(--text-body);
        line-height: 1.6;
        color: var(--text-primary);
    }

    .stMarkdown h2, .stMarkdown h3 {
        font-size: var(--text-heading) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        color: var(--text-primary);
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }

    .stMarkdown h4 {
        font-size: var(--text-body) !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
        color: var(--text-primary);
        margin-top: 0.25rem;
        margin-bottom: 0.5rem;
    }

    [data-testid="stCaptionContainer"], .stCaption {
        font-size: var(--text-sm) !important;
        color: var(--text-muted) !important;
        line-height: 1.45;
    }

    /* Masthead */
    .aether-masthead {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.45rem 1rem;
        padding-bottom: 0.9rem;
        margin-bottom: 1.15rem;
        border-bottom: 1px solid var(--border-hairline);
    }

    .aether-brand {
        display: flex;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 0.2rem 0.7rem;
    }

    .aether-wordmark {
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        color: var(--text-primary);
        line-height: 1.15;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-block;
        white-space: nowrap;
    }

    .aether-tagline {
        font-size: var(--text-sm);
        font-weight: 400;
        color: var(--text-muted);
        white-space: nowrap;
    }

    .aether-status-strip {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.4rem 0.95rem;
        font-size: var(--text-sm);
        color: var(--text-secondary);
    }

    .aether-status-item {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        white-space: nowrap;
    }

    .aether-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
        flex-shrink: 0;
    }

    .aether-dot--ok { background-color: var(--signal-ok); }
    .aether-dot--warn { background-color: var(--signal-medium); }
    .aether-dot--err { background-color: var(--signal-high); }
    .aether-dot--muted { background-color: var(--text-muted); }

    /* Architectural Metric Cards (inset top accent avoids rounded-corner pinching) */
    .aether-metric-card {
        position: relative;
        overflow: hidden;
        background: var(--bg-surface);
        border: 1px solid var(--border-hairline);
        border-radius: var(--radius-md);
        padding: 1.15rem 1.25rem 1.05rem 1.25rem;
        margin-bottom: 0.75rem;
        transition: border-color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
    }

    .aether-metric-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--card-accent, var(--border-strong));
    }

    .aether-metric-card:hover {
        border-color: var(--border-strong);
        box-shadow: 0 2px 10px -2px rgba(15, 23, 42, 0.06);
    }

    .aether-two-col-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem;
        align-items: stretch;
        margin-top: 0.25rem;
        margin-bottom: 1rem;
    }

    .aether-two-col-grid .aether-panel {
        margin-bottom: 0;
        height: 100%;
    }

    @media (max-width: 768px) {
        .aether-two-col-grid {
            grid-template-columns: 1fr;
        }
    }

    .aether-metric-label {
        font-size: var(--text-sm);
        font-weight: 500;
        color: var(--text-secondary);
        margin-bottom: 0.35rem;
    }

    .aether-metric-value {
        font-size: 1.85rem;
        font-weight: 600;
        letter-spacing: -0.025em;
        font-variant-numeric: tabular-nums;
        color: var(--text-primary);
        line-height: 1.15;
    }

    .aether-metric-sub {
        font-size: var(--text-sm);
        color: var(--text-muted);
        margin-top: 0.3rem;
    }

    /* Architectural Surface Panel */
    .aether-panel {
        background: var(--bg-surface);
        border: 1px solid var(--border-hairline);
        border-radius: var(--radius-md);
        padding: 1.25rem 1.4rem;
        margin-bottom: 1rem;
    }

    .aether-panel-title {
        font-size: var(--text-body);
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.35rem 0;
    }

    .aether-panel-copy {
        font-size: var(--text-sm);
        color: var(--text-secondary);
        line-height: 1.55;
        margin: 0;
        max-width: 65ch;
    }

    /* Signal Distribution Bar */
    .aether-signal-bar {
        display: flex;
        width: 100%;
        height: 8px;
        border-radius: 4px;
        overflow: hidden;
        background: var(--bg-subtle);
        margin: 0.75rem 0 0.6rem 0;
    }

    .aether-signal-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 1.25rem;
        font-size: var(--text-sm);
        color: var(--text-secondary);
        font-variant-numeric: tabular-nums;
    }

    /* Dashboard Top Findings Table-like Rows */
    .aether-finding-row {
        display: grid;
        grid-template-columns: 3.5rem 8.5rem 1fr auto;
        align-items: baseline;
        gap: 0.85rem;
        padding: 0.65rem 0;
        border-bottom: 1px solid var(--border-hairline);
        font-size: var(--text-sm);
    }

    .aether-finding-row:last-child {
        border-bottom: none;
        padding-bottom: 0;
    }

    .aether-finding-score {
        font-family: var(--font-mono);
        font-weight: 500;
        font-variant-numeric: tabular-nums;
    }

    .aether-finding-doc {
        font-family: var(--font-mono);
        color: var(--text-secondary);
        white-space: nowrap;
    }

    .aether-finding-title {
        color: var(--text-primary);
        font-weight: 500;
    }

    .aether-finding-status {
        color: var(--text-muted);
        white-space: nowrap;
    }

    @media (max-width: 768px) {
        .aether-finding-row {
            grid-template-columns: 3.2rem 1fr;
            gap: 0.35rem 0.75rem;
        }
        .aether-finding-doc, .aether-finding-status {
            grid-column: 2;
        }
    }

    /* Patent Dossier Header */
    .aether-dossier-header {
        position: relative;
        overflow: hidden;
        background: var(--bg-surface);
        border: 1px solid var(--border-hairline);
        border-radius: var(--radius-md);
        padding: 1.35rem 1.5rem;
        margin-bottom: 1.25rem;
    }

    .aether-dossier-header::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: var(--card-accent, var(--border-strong));
    }

    .aether-dossier-title {
        font-size: var(--text-heading);
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--text-primary);
        line-height: 1.3;
        margin: 0 0 0.35rem 0;
    }

    .aether-dossier-subtitle {
        font-size: var(--text-body);
        color: var(--text-secondary);
        margin: 0 0 0.85rem 0;
    }

    .aether-meta-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem 1.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid var(--border-hairline);
        font-size: var(--text-sm);
    }

    .aether-meta-item {
        color: var(--text-secondary);
    }

    .aether-meta-key {
        color: var(--text-muted);
        margin-right: 0.35rem;
    }

    .aether-meta-val {
        color: var(--text-primary);
        font-weight: 500;
    }

    .aether-links-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 1.25rem;
        margin-top: 0.75rem;
        font-size: var(--text-sm);
    }

    .aether-link {
        color: var(--accent) !important;
        text-decoration: none !important;
        font-weight: 500;
        transition: color 160ms var(--ease-out);
    }

    .aether-link:hover {
        color: var(--accent-hover) !important;
        text-decoration: underline !important;
    }

    /* Reading Surface for Patent Abstracts */
    .aether-abstract {
        background: var(--bg-surface);
        border: 1px solid var(--border-hairline);
        border-radius: var(--radius-md);
        padding: 1.2rem 1.35rem;
        color: var(--text-primary);
        font-size: var(--text-body);
        line-height: 1.7;
        margin-bottom: 0.9rem;
    }

    .aether-abstract--muted {
        background: var(--bg-subtle);
        color: var(--text-secondary);
        font-size: var(--text-sm);
        line-height: 1.6;
    }

    /* Plain Typographic Tag List (no decorative pills) */
    .aether-tag-list {
        font-size: var(--text-sm);
        color: var(--text-secondary);
        line-height: 1.65;
        margin: 0.25rem 0 0.75rem 0;
    }

    .aether-tag-sep {
        color: var(--border-strong);
        margin: 0 0.4rem;
    }

    /* Status inline indicator */
    .aether-inline-status {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: var(--text-sm);
        font-weight: 500;
        color: var(--text-primary);
        margin-right: 0.85rem;
    }

    /* Sidebar Refinement */
    section[data-testid="stSidebar"] {
        background-color: var(--bg-surface);
        border-right: 1px solid var(--border-hairline);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
        padding-left: 1.25rem !important;
        padding-right: 1.25rem !important;
    }

    .aether-sidebar-title {
        font-size: var(--text-body);
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.75rem 0;
        letter-spacing: -0.01em;
    }

    .aether-conn-list {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        margin: 0.25rem 0 0.5rem 0;
    }

    .aether-conn-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: var(--text-sm);
        color: var(--text-secondary);
        padding: 0.25rem 0;
    }

    /* Tabs: crisp underline navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 1px solid var(--border-hairline);
        margin-bottom: 1.25rem;
        background: transparent;
    }

    .stTabs button[data-baseweb="tab"],
    .stTabs button[role="tab"] {
        height: auto !important;
        padding: 0.6rem 0.95rem !important;
        border-radius: 0 !important;
        background-color: transparent !important;
        color: var(--text-secondary) !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        font-weight: 500;
        transition: color 160ms var(--ease-out), border-color 160ms var(--ease-out);
    }

    .stTabs button[data-baseweb="tab"] p,
    .stTabs button[role="tab"] p {
        margin: 0 !important;
        font-size: var(--text-sm) !important;
        font-weight: 500;
    }

    .stTabs button[data-baseweb="tab"]:hover,
    .stTabs button[role="tab"]:hover {
        color: var(--text-primary) !important;
        background-color: transparent !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--text-primary) !important;
        border-bottom: 2px solid var(--accent) !important;
    }

    .stTabs [aria-selected="true"] p {
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }

    /* Hide Streamlit's default red tab highlight bar if present */
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--accent) !important;
        height: 2px !important;
    }

    /* Buttons */
    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: var(--radius-sm);
        font-size: var(--text-sm);
        font-weight: 500;
        padding: 0.45rem 0.95rem;
        min-height: 2.35rem;
        border: 1px solid var(--border-strong);
        background-color: var(--bg-surface);
        color: var(--text-primary);
        transition: background-color 160ms var(--ease-out), border-color 160ms var(--ease-out), color 160ms var(--ease-out), box-shadow 160ms var(--ease-out);
        white-space: nowrap;
    }

    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        border-color: var(--accent);
        background-color: var(--bg-subtle);
        color: var(--text-primary);
    }

    div.stButton > button[kind="primary"] {
        background-color: var(--accent);
        border-color: var(--accent);
        color: #FFFFFF;
        font-weight: 600;
    }

    div.stButton > button[kind="primary"]:hover {
        background-color: var(--accent-hover);
        border-color: var(--accent-hover);
        color: #FFFFFF;
    }

    div.stButton > button:disabled,
    div.stDownloadButton > button:disabled {
        background-color: var(--bg-subtle) !important;
        border-color: var(--border-hairline) !important;
        color: var(--text-muted) !important;
        opacity: 1 !important;
        cursor: not-allowed;
    }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: var(--bg-surface);
        border: 1px solid var(--border-hairline);
        border-radius: var(--radius-md);
    }

    [data-testid="stExpander"] summary {
        font-size: var(--text-sm);
        font-weight: 500;
        color: var(--text-primary);
    }

    /* Inline code */
    code {
        color: var(--text-primary);
        background: var(--bg-subtle);
        border: 1px solid var(--border-hairline);
        padding: 0.1rem 0.35rem;
        border-radius: 4px;
        font-size: 0.85em;
    }

    /* Dividers */
    hr {
        border-color: var(--border-hairline) !important;
        margin: 1.25rem 0 !important;
    }

    /* Hide the underlying file uploader widget triggered by Upload/Replace PDF button */
    .st-key-aether_hidden_pdf_uploader_wrap {
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            transition-duration: 0.01ms !important;
            animation-duration: 0.01ms !important;
        }
    }
</style>
""",
        unsafe_allow_html=True,
    )
