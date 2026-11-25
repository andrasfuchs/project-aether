import html

import streamlit as st


def render_metric_card(label, value, subtext="", color="#00B4D8", dimmed=False):
    """Helper to render a custom HTML metric card."""
    dim_style = "opacity: 0.55; filter: grayscale(0.35);" if dimmed else ""
    safe_label = html.escape(str(label))
    safe_value = html.escape(str(value))
    safe_subtext = html.escape(str(subtext))
    st.markdown(
        f"""
    <div class="glass-card" style="box-shadow: inset 4px 0 0 0 {color}; {dim_style}">
        <div class="metric-label">{safe_label}</div>
        <div class="metric-value" style="color: {color};">{safe_value}</div>
        <div class="metric-subtext">{safe_subtext}</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def show_placeholder_dashboard():
    """Display modern placeholder dashboard."""
    st.markdown("### Search Status: Idle")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Total Results", "—", "Awaiting search", "#94A3B8")
    with col2:
        render_metric_card("High Value", "—", "High-signal patents", "#EF4444")
    with col3:
        render_metric_card("Medium Value", "—", "Potential interest", "#F59E0B")
    with col4:
        render_metric_card("Low Value", "—", "Probable noise", "#00B4D8")


def render_dashboard_metrics(dashboard):
    """Render the dashboard with final SearchRunResult metrics."""
    st.markdown("### Search Status: Completed")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_metric_card("Total Results", dashboard.total_patents_searched, "Patents Scanned", "#94A3B8")
    with col2:
        render_metric_card("High Value", dashboard.high_priority_count, "Critical Findings", "#EF4444")
    with col3:
        render_metric_card("Medium Value", dashboard.medium_priority_count, "Potential Interest", "#F59E0B")
    with col4:
        render_metric_card("Low Value", dashboard.low_priority_count, "Probable Noise", "#00B4D8")


def render_dashboard_progress(dashboard_container, event) -> None:
    """Render live progress updates into a Streamlit container."""
    with dashboard_container.container():
        if event.progress_percent <= 0:
            show_placeholder_dashboard()
            return

        dimmed = 0 < event.progress_percent < 100
        dim_style = "opacity: 0.6; filter: grayscale(0.35);" if dimmed else ""

        st.markdown(
            f'<h3 style="{dim_style}">Search Status: {html.escape(event.status_text)}</h3>',
            unsafe_allow_html=True,
        )

        if dimmed:
            st.progress(event.progress_percent / 100.0, text=f"Progress: {event.progress_percent}%")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("Total Results", str(event.total_scanned), "Patents Scanned", "#94A3B8", dimmed=dimmed)
        with col2:
            render_metric_card("High Value", str(event.high_count), "Critical Findings", "#EF4444", dimmed=dimmed)
        with col3:
            render_metric_card("Medium Value", str(event.medium_count), "Potential Interest", "#F59E0B", dimmed=dimmed)
        with col4:
            render_metric_card("Low Value", str(event.low_count), "Probable Noise", "#00B4D8", dimmed=dimmed)
