import logging

import streamlit as st

from project_aether.core.log_stream import get_log_stream_handler


LOG_LEVEL_OPTIONS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def render_live_logs_tab() -> None:
    """Render a live log stream panel for production diagnostics."""
    st.markdown("### Live Log Stream")
    st.caption("Tail the in-process runtime logs captured by the server worker.")

    handler = get_log_stream_handler()
    if handler is None:
        st.warning("Live log stream handler is not initialized.")
        return

    col1, col2, col3, col4 = st.columns([1.2, 1, 1.4, 1.4])
    with col1:
        selected_level = st.selectbox(
            "Minimum level",
            LOG_LEVEL_OPTIONS,
            index=0,
            key="live_logs_min_level",
        )
    with col2:
        line_limit = st.slider("Max lines", 50, 2000, 400, key="live_logs_line_limit")
    with col3:
        logger_filter = st.text_input(
            "Logger contains",
            key="live_logs_logger_filter",
            placeholder="ProjectAether, TranslationService, AnalystAgent...",
        )
    with col4:
        text_filter = st.text_input(
            "Message contains",
            key="live_logs_text_filter",
            placeholder="quota, translation, failed...",
        )

    action_col1, action_col2, action_col3, action_col4 = st.columns([1, 1, 1.2, 2.8])
    with action_col1:
        refresh_clicked = st.button("Refresh", key="live_logs_refresh")
    with action_col2:
        clear_clicked = st.button("Clear", key="live_logs_clear")
    with action_col3:
        auto_refresh = st.toggle("Auto refresh", value=True, key="live_logs_auto_refresh")
    with action_col4:
        refresh_seconds = st.selectbox(
            "Refresh interval",
            [1, 2, 5, 10],
            index=1,
            key="live_logs_refresh_seconds",
            disabled=not auto_refresh,
        )

    if clear_clicked:
        handler.clear()
        st.success("Log buffer cleared.")

    level_no = getattr(logging, selected_level, logging.DEBUG)

    def _render_log_output() -> None:
        entries = handler.snapshot(
            min_level=level_no,
            logger_filter=logger_filter,
            text_filter=text_filter,
            limit=line_limit,
        )
        total_entries = handler.total_entries()
        st.caption(
            f"Showing {len(entries)} line(s) | Total buffered: {total_entries} | Level: {selected_level}+"
        )
        if not entries:
            st.info("No log lines match the current filters.")
            return

        text_blob = "\n".join(entry.formatted for entry in entries)
        st.download_button(
            "Download visible logs",
            data=text_blob,
            file_name="project_aether_live_logs.txt",
            mime="text/plain",
            key="live_logs_download",
        )
        st.code(text_blob, language="text")

    if auto_refresh and hasattr(st, "fragment"):

        @st.fragment(run_every=f"{refresh_seconds}s")
        def _live_fragment() -> None:
            _render_log_output()

        _live_fragment()
    else:
        if auto_refresh and not hasattr(st, "fragment"):
            st.caption("Auto-refresh is not supported in this Streamlit build. Use Refresh.")
        if refresh_clicked or not auto_refresh:
            _render_log_output()
        else:
            _render_log_output()
