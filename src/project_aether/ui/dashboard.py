import streamlit as st


def render_metric_card(label, value, subtext="", color="#00B4D8"):
    """Helper to render a custom HTML metric card."""
    st.markdown(
        f"""
    <div class="glass-card" style="border-left: 4px solid {color};">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
        <div style="color: #64748b; font-size: 0.8rem; margin-top: 0.5rem;">{subtext}</div>
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
