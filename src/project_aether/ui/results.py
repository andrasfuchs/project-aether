"""
Interactive Search Results tab with filtering, saved review grades, and CSV/Markdown export.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from project_aether.core.reviews import get_reviews_map


def _status_label(assessment) -> str:
    sa = assessment.status_analysis
    if sa.is_refused:
        return "Refused"
    if sa.is_withdrawn:
        return "Withdrawn"
    if sa.is_expired:
        return "Expired"
    if sa.is_inactive:
        return "Inactive"
    if sa.is_active:
        return "Active"
    if sa.is_pending:
        return "Pending"
    original = sa.original_status or "UNKNOWN"
    return f"Other ({original})"


def render_results_tab(assessments, jurisdiction_map):
    if not assessments:
        st.info("No results yet. Run an analysis to populate the table.")
        return

    sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)
    reviews_map = get_reviews_map([a.record_id for a in sorted_assessments])

    jurisdiction_code_to_name = {v: k for k, v in jurisdiction_map.items()}
    jurisdiction_code_to_name["WO"] = "WO - PCT application"

    # --- FILTER BAR ---
    fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(
        [1.1, 1.3, 1.1, 1.6, 1.2], vertical_alignment="bottom"
    )
    with fcol1:
        min_score = st.slider("Min Relevance", 0, 100, 0, key="results_min_score")
    with fcol2:
        priority_filter = st.multiselect(
            "Priority",
            ["HIGH", "MEDIUM", "LOW"],
            default=["HIGH", "MEDIUM", "LOW"],
            key="results_priority_filter",
        )
    with fcol3:
        all_statuses = sorted({_status_label(a) for a in sorted_assessments})
        status_filter = st.multiselect(
            "Status",
            all_statuses,
            default=[],
            placeholder="All statuses",
            key="results_status_filter",
        )
    with fcol4:
        text_query = st.text_input(
            "Filter text",
            placeholder="Search title, tags, rationale...",
            key="results_text_filter",
        ).strip().lower()
    with fcol5:
        hide_noise = st.checkbox(
            "Hide reviewed noise (≤30)",
            value=False,
            key="results_hide_noise",
        )

    rows = []
    filtered_assessments = []
    for a in sorted_assessments:
        if a.relevance_score < min_score:
            continue
        if priority_filter and a.intelligence_value not in priority_filter:
            continue
        status_disp = _status_label(a)
        if status_filter and status_disp not in status_filter:
            continue

        review = reviews_map.get(a.record_id)
        my_score = float(review["user_score"]) if review is not None else None
        if hide_noise and my_score is not None and my_score <= 30.0:
            continue

        display_title = a.title_en or a.title or "Untitled"
        if text_query:
            haystack = " ".join(
                [
                    a.record_id,
                    a.doc_number,
                    display_title,
                    a.title or "",
                    a.rationale or "",
                    a.domain_category or "",
                    " ".join(a.llm_tags or []),
                ]
            ).lower()
            if text_query not in haystack:
                continue

        filtered_assessments.append(a)
        rows.append(
            {
                "Record ID": a.record_id,
                "Patent #": f"{a.jurisdiction} {a.doc_number}".strip(),
                "Title": display_title,
                "Priority": a.intelligence_value,
                "Relevance Score": round(float(a.relevance_score), 1),
                "My Score": round(my_score, 1) if my_score is not None else None,
                "Status": status_disp,
                "Category": a.domain_category or "—",
                "Notes": (review.get("notes") or "") if review else "",
                "Link": a.provider_record_url or "",
            }
        )

    st.caption(f"Showing {len(rows)} of {len(sorted_assessments)} patents. Click any row to load it in Detailed Analysis.")

    if not rows:
        st.warning("No patents match the active filters.")
        return

    df = pd.DataFrame(rows)

    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "Relevance Score": st.column_config.ProgressColumn(
                "Relevance Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "My Score": st.column_config.NumberColumn(
                "My Score",
                min_value=0,
                max_value=100,
                format="%.0f",
            ),
            "Link": st.column_config.LinkColumn("Provider", display_text="Open"),
        },
        height=520,
    )

    selection_obj = getattr(event, "selection", None)
    selected_rows = getattr(selection_obj, "rows", []) if selection_obj else []
    if selected_rows:
        selected_idx = selected_rows[0]
        selected_record_id = df.iloc[selected_idx]["Record ID"]
        st.session_state["selected_record_id_for_analysis"] = selected_record_id
        st.success(
            f"Selected **{selected_record_id}** ({df.iloc[selected_idx]['Patent #']}). "
            "Open the **Detailed Analysis** tab to inspect, translate, or save George's review."
        )

    # --- EXPORT ---
    exp_col1, exp_col2, _ = st.columns([1, 1, 4])
    with exp_col1:
        st.download_button(
            "Export CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="project_aether_results.csv",
            mime="text/csv",
            width="stretch",
        )
    with exp_col2:
        md_lines = ["# Project Aether Search Results", ""]
        for r in rows:
            my_s = f"{r['My Score']:.0f}/100" if r["My Score"] is not None else "Unreviewed"
            md_lines.append(
                f"- **[{r['Patent #']}] {r['Title']}** | Relevance: {r['Relevance Score']:.1f} | "
                f"George: {my_s} | Status: {r['Status']} | {r['Link']}"
            )
        st.download_button(
            "Export Markdown",
            data="\n".join(md_lines).encode("utf-8"),
            file_name="project_aether_results.md",
            mime="text/markdown",
            width="stretch",
        )
