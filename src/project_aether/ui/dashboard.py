import html

import streamlit as st


def render_metric_card(label, value, subtext="", color="#475569", dimmed=False):
    """Render an architectural KPI card with hairline border and top accent rule."""
    dim_style = "opacity: 0.55;" if dimmed else ""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_subtext = html.escape(str(subtext))
    st.markdown(
        f"""
        <div class="aether-metric-card" style="--card-accent: {color}; {dim_style}">
            <div class="aether-metric-label">{safe_label}</div>
            <div class="aether-metric-value" style="color: {color};">{safe_value}</div>
            <div class="aether-metric-sub">{safe_subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_placeholder_dashboard(
    keyword_set_name: str = "",
    include_count: int = 0,
    exclude_count: int = 0,
    languages: list[str] | None = None,
):
    """Display an informative idle dashboard with active query profile and workflow summary."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Total scanned", "-", "Awaiting search", "#475569")
    with col2:
        render_metric_card("High signal", "-", "Critical findings", "#DC2626")
    with col3:
        render_metric_card("Medium signal", "-", "Potential interest", "#D97706")
    with col4:
        render_metric_card("Low signal", "-", "Probable noise", "#2563EB")

    langs_str = ", ".join(languages) if languages else "English"
    set_disp = html.escape(keyword_set_name) if keyword_set_name else "Untitled query"

    st.markdown(
        f"""
        <div class="aether-two-col-grid">
            <div class="aether-panel">
                <div class="aether-panel-title">Active query profile</div>
                <div class="aether-meta-grid" style="border-top: none; padding-top: 0.35rem;">
                    <span class="aether-meta-item"><span class="aether-meta-key">Set</span><span class="aether-meta-val">{set_disp}</span></span>
                    <span class="aether-meta-item"><span class="aether-meta-key">Languages</span><span class="aether-meta-val">{html.escape(langs_str)}</span></span>
                    <span class="aether-meta-item"><span class="aether-meta-key">Terms</span><span class="aether-meta-val">{include_count} include · {exclude_count} exclude</span></span>
                </div>
                <p class="aether-panel-copy" style="margin-top: 0.85rem;">
                    Review or adjust your keyword groups in the sidebar, then select <strong>Run search</strong> to retrieve, translate, and score matching patents.
                </p>
            </div>
            <div class="aether-panel">
                <div class="aether-panel-title">Research triage workflow</div>
                <p class="aether-panel-copy">
                    Retrieve multilingual patent records from EPO OPS with automatic Lens fallback, decode INPADOC legal status events, and score technical relevance with Gemini.
                    Inspect top candidates in <strong>Detailed Analysis</strong> to read translated abstracts, generate PDF technical briefs, and record calibration scores.
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dashboard_metrics(dashboard, assessments=None):
    """Render completed search metrics, signal distribution bar, and top findings."""
    total = int(dashboard.total_patents_searched or 0)
    high = int(dashboard.high_priority_count or 0)
    medium = int(dashboard.medium_priority_count or 0)
    low = int(dashboard.low_priority_count or 0)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Total scanned", total, "Patents evaluated", "#0F172A")
    with col2:
        render_metric_card("High signal", high, "Critical findings", "#DC2626")
    with col3:
        render_metric_card("Medium signal", medium, "Potential interest", "#D97706")
    with col4:
        render_metric_card("Low signal", low, "Probable noise", "#2563EB")

    if total > 0:
        high_pct = (high / total) * 100
        med_pct = (medium / total) * 100
        low_pct = (low / total) * 100
        st.markdown(
            f"""
            <div class="aether-panel">
                <div class="aether-panel-title">Signal distribution</div>
                <div class="aether-signal-bar">
                    <div style="width: {high_pct:.2f}%; background: #DC2626;"></div>
                    <div style="width: {med_pct:.2f}%; background: #D97706;"></div>
                    <div style="width: {low_pct:.2f}%; background: #94A3B8;"></div>
                </div>
                <div class="aether-signal-legend">
                    <span class="aether-status-item"><span class="aether-dot aether-dot--err"></span>High {high} ({high_pct:.1f}%)</span>
                    <span class="aether-status-item"><span class="aether-dot aether-dot--warn"></span>Medium {medium} ({med_pct:.1f}%)</span>
                    <span class="aether-status-item"><span class="aether-dot aether-dot--muted"></span>Low {low} ({low_pct:.1f}%)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if assessments:
        top_items = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)[:6]
        rows_html = []
        for item in top_items:
            score_color = "#475569"
            if item.intelligence_value == "HIGH":
                score_color = "#DC2626"
            elif item.intelligence_value == "MEDIUM":
                score_color = "#D97706"
            doc_str = f"{item.jurisdiction} {item.doc_number}".strip()
            title_str = item.title_en or item.title or "Untitled"
            sa = getattr(item, "status_analysis", None)
            status_str = ""
            if sa:
                if sa.is_refused:
                    status_str = "Refused"
                elif sa.is_withdrawn:
                    status_str = "Withdrawn"
                elif sa.is_expired:
                    status_str = "Expired"
                elif sa.is_active:
                    status_str = "Active"
                elif sa.is_pending:
                    status_str = "Pending"
                else:
                    status_str = sa.original_status or ""
            rows_html.append(
                f'<div class="aether-finding-row">'
                f'<span class="aether-finding-score" style="color: {score_color};">{item.relevance_score:.1f}</span>'
                f'<span class="aether-finding-doc">{html.escape(doc_str)}</span>'
                f'<span class="aether-finding-title">{html.escape(title_str)}</span>'
                f'<span class="aether-finding-status">{html.escape(status_str)}</span>'
                f"</div>"
            )
        st.markdown(
            f"""
            <div class="aether-panel">
                <div class="aether-panel-title">Highest-ranked findings</div>
                {''.join(rows_html)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_dashboard_progress(dashboard_container, event) -> None:
    """Render live progress updates into a Streamlit container."""
    with dashboard_container.container():
        if event.progress_percent <= 0:
            show_placeholder_dashboard()
            return

        dimmed = 0 < event.progress_percent < 100
        st.markdown(f"### {html.escape(event.status_text)}")

        if dimmed:
            st.progress(event.progress_percent / 100.0, text=f"Progress: {event.progress_percent}%")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("Total scanned", str(event.total_scanned), "Patents evaluated", "#0F172A", dimmed=dimmed)
        with col2:
            render_metric_card("High signal", str(event.high_count), "Critical findings", "#DC2626", dimmed=dimmed)
        with col3:
            render_metric_card("Medium signal", str(event.medium_count), "Potential interest", "#D97706", dimmed=dimmed)
        with col4:
            render_metric_card("Low signal", str(event.low_count), "Probable noise", "#2563EB", dimmed=dimmed)
