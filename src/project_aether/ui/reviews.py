"""
Reviewed Patents tab for George: browse, filter, edit, export/import saved
0-100 grades and notes, and generate LLM query refinement suggestions.
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.keyword_translation import (
    ensure_keyword_set,
    save_keyword_cache,
)
from project_aether.core.llm_advisor import suggest_query_refinements
from project_aether.core.reviews import (
    delete_review,
    export_reviews_json,
    import_reviews_json,
    list_reviews,
    save_review,
)


def render_reviews_tab() -> None:
    st.markdown("### George's Reviewed Patents")
    st.caption(
        "All saved 0–100 grades and notes persist in `data/aether.db` across sessions "
        "and calibrate future relevance scoring."
    )

    all_reviews = list_reviews()

    # --- FILTER BAR ---
    f1, f2, f3 = st.columns([1.4, 1.8, 1.2])
    with f1:
        tier = st.selectbox(
            "Score filter",
            ["All", "Relevant (≥60)", "Maybe (31–59)", "Noise (≤30)"],
            key="reviews_tab_tier",
        )
    with f2:
        search_text = st.text_input(
            "Search reviewed patents",
            placeholder="Title, patent #, record ID, notes...",
            key="reviews_tab_search",
        )
    with f3:
        st.metric("Total Reviewed", len(all_reviews))

    min_s, max_s = None, None
    if tier == "Relevant (≥60)":
        min_s = 60.0
    elif tier == "Maybe (31–59)":
        min_s, max_s = 31.0, 59.99
    elif tier == "Noise (≤30)":
        max_s = 30.0

    reviews = list_reviews(min_score=min_s, max_score=max_s, search_text=search_text)

    if not reviews:
        st.info("No reviewed patents match the current filter. Grade patents in the Detailed Analysis tab.")
    else:
        rows = [
            {
                "Record ID": r["record_id"],
                "Patent #": f"{r['jurisdiction']} {r['doc_number']}".strip(),
                "Title": r["title_en"] or r["title"] or "Untitled",
                "George Score": round(float(r["user_score"]), 1),
                "Relevance Score": round(float(r["llm_score"]), 1) if r.get("llm_score") is not None else None,
                "Calibrate": bool(r.get("use_for_calibration", 1)),
                "Notes": r.get("notes") or "",
                "Updated": (r.get("updated_at") or "")[:19].replace("T", " "),
            }
            for r in reviews
        ]
        df = pd.DataFrame(rows)
        event = st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "George Score": st.column_config.ProgressColumn(
                    "George Score", min_value=0, max_value=100, format="%.0f"
                ),
                "Relevance Score": st.column_config.NumberColumn(
                    "Relevance Score", min_value=0, max_value=100, format="%.1f"
                ),
            },
            height=340,
        )

        selection_obj = getattr(event, "selection", None)
        selected_rows = getattr(selection_obj, "rows", []) if selection_obj else []
        default_rid = df.iloc[selected_rows[0]]["Record ID"] if selected_rows else reviews[0]["record_id"]
        target = next((r for r in reviews if r["record_id"] == default_rid), reviews[0])

        with st.expander(
            f"Edit Review: {target['record_id']} — {target['title_en'] or target['title']}",
            expanded=bool(selected_rows),
        ):
            if target.get("provider_record_url"):
                st.markdown(f"[View on Provider]({target['provider_record_url']})")
            if target.get("abstract"):
                st.caption(target["abstract"][:600] + ("..." if len(target["abstract"]) > 600 else ""))

            new_score = st.slider(
                "George's Score (0–100)",
                0,
                100,
                round(float(target["user_score"])),
                key=f"rev_edit_score_{target['record_id']}",
            )
            new_notes = st.text_area(
                "Notes",
                value=target.get("notes") or "",
                key=f"rev_edit_notes_{target['record_id']}",
            )
            new_cal = st.checkbox(
                "Use to calibrate relevance scoring",
                value=bool(target.get("use_for_calibration", 1)),
                key=f"rev_edit_cal_{target['record_id']}",
            )
            b1, b2, _ = st.columns([1, 1, 3])
            with b1:
                if st.button("Update Review", key=f"rev_save_{target['record_id']}", type="primary"):
                    save_review(
                        record_id=target["record_id"],
                        user_score=new_score,
                        notes=new_notes,
                        use_for_calibration=new_cal,
                    )
                    st.success("Review updated.")
                    st.rerun()
            with b2:
                if st.button("Delete Review", key=f"rev_del_{target['record_id']}"):
                    delete_review(target["record_id"])
                    st.warning("Review deleted.")
                    st.rerun()

    st.markdown("---")

    # --- LLM QUERY REFINEMENT ADVISOR ---
    st.markdown("#### Query & Exclude-Term Advisor")
    st.caption(
        "Use Gemini to inspect your low-scored noise vs. high-scored patents and suggest "
        "new exclude terms or evasive-terminology synonyms."
    )
    if st.button("Suggest Query Refinements", disabled=len(all_reviews) < 2):
        config = get_config()
        api_key = config.google_api_key or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            st.warning("GEMINI_API_KEY not configured.")
        else:
            kw_cfg: dict = st.session_state.get("keyword_config") or {"English": {"positive": [], "negative": []}}
            inc, exc = get_active_english_keywords(kw_cfg)
            advisor_model = st.session_state.get("llm_advisor_model", config.llm_advisor_model)
            advisor_thinking = st.session_state.get("llm_advisor_thinking_level", config.llm_advisor_thinking_level)
            with st.spinner("Analyzing reviewed patents..."):
                suggestions = suggest_query_refinements(
                    reviews=all_reviews,
                    active_include=inc,
                    active_exclude=exc,
                    api_key=api_key,
                    model=advisor_model,
                    thinking_level=advisor_thinking,
                )
            st.session_state["query_refinement_suggestions"] = suggestions

    suggestions = st.session_state.get("query_refinement_suggestions")
    if suggestions:
        st.info(suggestions.get("summary") or "")
        suggested_excludes = suggestions.get("suggested_excludes") or []
        if suggested_excludes:
            st.write("**Suggested Exclude Terms:**", ", ".join(f"`{t}`" for t in suggested_excludes))
            if st.button("Add Suggested Excludes to Active Keyword Set"):
                kw_cfg: dict = st.session_state.get("keyword_config") or {"English": {"positive": [], "negative": []}}
                current_exc = kw_cfg.setdefault("English", {}).get("negative", [])
                merged = list(dict.fromkeys([*current_exc, *suggested_excludes]))
                kw_cfg["English"]["negative"] = merged
                st.session_state["keyword_config"] = kw_cfg
                st.session_state["keyword_widget_version"] = st.session_state.get("keyword_widget_version", 0) + 1
                cache = st.session_state.get("keyword_cache")
                if cache is not None:
                    inc, exc = get_active_english_keywords(kw_cfg)
                    ensure_keyword_set(cache, inc, exc, label=st.session_state.get("keyword_set_name"))
                    save_keyword_cache(cache)
                st.success(f"Added {len(suggested_excludes)} exclude terms to active keyword set.")
                st.rerun()

        suggested_inc = suggestions.get("suggested_include_synonyms") or []
        if suggested_inc:
            st.write("**Suggested Positive Synonym Groups:**")
            for grp in suggested_inc:
                st.markdown(f"- `{', '.join(grp)}`")

    st.markdown("---")

    # --- BACKUP / SHARING (JSON EXPORT / IMPORT) ---
    st.markdown("#### Backup & Share Reviews (JSON)")
    ex_col, im_col = st.columns(2, vertical_alignment="bottom")
    with ex_col:
        st.download_button(
            "Export Reviews JSON",
            data=export_reviews_json().encode("utf-8"),
            file_name="aether_reviews.json",
            mime="application/json",
            width="stretch",
        )
    with im_col:
        uploaded = st.file_uploader("Import Reviews JSON", type=["json"], key="reviews_import_uploader")
        if uploaded is not None:
            try:
                count = import_reviews_json(uploaded.read().decode("utf-8"))
                st.success(f"Imported/updated {count} review(s).")
                st.rerun()
            except Exception as exc:
                st.error(f"Import failed: {exc}")
