"""
Detailed Analysis tab: inspect patent metadata, on-demand English/Hungarian
translation (disk-cached), Deep Technical Brief, and George's 0-100 review form.
"""

from __future__ import annotations

import asyncio
import html
import os
from typing import Any

import streamlit as st

from project_aether.core.config import get_config
from project_aether.core.llm_advisor import (
    delete_patent_pdf,
    fetch_google_patents_pdf,
    generate_technical_brief,
    load_patent_pdf,
    save_patent_pdf,
)
from project_aether.core.reviews import delete_review, get_review, save_review
from project_aether.core.translation_service import (
    get_cached_translation,
    load_translation_cache,
    set_cached_translation,
    translate_text,
)
from project_aether.tools.lens_api import LensConnector


def _extract_text_field(value: Any) -> str:
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict) and item.get("text"):
                parts.append(str(item["text"]))
            elif item:
                parts.append(str(item))
        return "\n\n".join(parts)
    if isinstance(value, dict):
        return str(value.get("text") or "")
    return str(value or "")


def _extract_claims_text(patent_data: dict[str, Any]) -> str:
    return _extract_text_field(patent_data.get("claims_en") or patent_data.get("claims"))


def render_deep_dive(assessment) -> None:
    """Render a detailed view of a patent assessment."""
    config = get_config()
    api_key = config.google_api_key or os.getenv("GEMINI_API_KEY", "")

    color = "#94A3B8"
    if assessment.intelligence_value == "HIGH":
        color = "#EF4444"
    elif assessment.intelligence_value == "MEDIUM":
        color = "#F59E0B"

    patent_data: dict[str, Any] = next(
        (
            p
            for p in st.session_state.get("all_raw_results", [])
            if p.get("record_id") == assessment.record_id
        ),
        {},
    )

    provider_url = assessment.provider_record_url
    legal_history_url = getattr(assessment, "legal_history_url", None) or patent_data.get(
        "legal_history_url"
    )
    english_title = getattr(assessment, "title_en", None) or patent_data.get("title_en")

    safe_title = html.escape(assessment.title or "Untitled")
    title_html = f"<h2>{safe_title}</h2>"
    if english_title and english_title.strip().lower() != (assessment.title or "").strip().lower():
        title_html += (
            f'<p style="font-size: 0.98rem; color: #94A3B8; margin-top: -10px;">'
            f"({html.escape(english_title)})</p>"
        )

    inventors_str = ", ".join(assessment.inventors) if assessment.inventors else "Unknown"
    applicants = getattr(assessment, "applicants", None) or []
    applicants_str = ", ".join(applicants) if applicants else "—"
    pub_date = getattr(assessment, "date_published", None) or patent_data.get("date_published") or "Unknown"

    st.markdown(
        f"""
    <div class="glass-card" style="box-shadow: inset 0 3px 0 0 {color};">
        {title_html}
        <p style="color: #CBD5E1; font-size: 0.9rem; margin: 0.35rem 0;">
            <strong>Inventors:</strong> {html.escape(inventors_str)} &nbsp;|&nbsp;
            <strong>Applicants:</strong> {html.escape(applicants_str)} &nbsp;|&nbsp;
            <strong>Published:</strong> {html.escape(str(pub_date))}
        </p>
        <p style="font-family: monospace; color: #94A3B8; font-size: 0.9rem; margin: 0.35rem 0;">
            {html.escape(assessment.record_id)} &nbsp;·&nbsp; {html.escape(assessment.jurisdiction)} {html.escape(assessment.doc_number)}
            {f" &nbsp;·&nbsp; <span style='color: #7DD3FC;'>{html.escape(assessment.domain_category)}</span>" if getattr(assessment, "domain_category", "") else ""}
        </p>
        <div style="margin-top: 0.5rem; display: flex; gap: 1rem; font-size: 0.88rem;">
            {
                f'<a href="{html.escape(provider_url)}" target="_blank" style="color: #38BDF8; text-decoration: none;">View on Provider ↗</a>'
                if provider_url
                else '<span style="color: #64748B;">No external patent link available.</span>'
            }
            {
                f'<a href="{html.escape(legal_history_url)}" target="_blank" style="color: #34D399; text-decoration: none;">Legal History ↗</a>'
                if legal_history_url
                else ''
            }
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Abstract")
        abstract_data = patent_data.get("abstract", None)
        translation_cache = load_translation_cache()
        trans_model = st.session_state.get("llm_translation_model", config.llm_translation_model)
        trans_thinking = st.session_state.get(
            "llm_translation_thinking_level", config.llm_translation_thinking_level
        )

        primary_abstract_text = ""

        if abstract_data:
            if isinstance(abstract_data, list):
                lang_map = {
                    "en": "English",
                    "fr": "French",
                    "de": "German",
                    "es": "Spanish",
                    "it": "Italian",
                    "pt": "Portuguese",
                    "ru": "Russian",
                    "zh": "Chinese",
                    "ja": "Japanese",
                    "ko": "Korean",
                    "hu": "Hungarian",
                    "ar": "Arabic",
                    "pl": "Polish",
                    "ro": "Romanian",
                    "cs": "Czech",
                    "nl": "Dutch",
                    "sv": "Swedish",
                    "no": "Norwegian",
                    "fi": "Finnish",
                }
                available_abstracts: dict[str, str] = {}
                for abstract_obj in abstract_data:
                    if not isinstance(abstract_obj, dict):
                        continue
                    lang_code = str(abstract_obj.get("lang", "unknown")).lower()
                    lang_name = lang_map.get(lang_code, lang_code.upper())
                    if abstract_obj.get("text"):
                        available_abstracts[lang_name] = abstract_obj.get("text", "")

                if available_abstracts:
                    primary_abstract_text = next(iter(available_abstracts.values()))

                abstract_en = patent_data.get("abstract_en")
                if abstract_en and "English" not in available_abstracts:
                    available_abstracts["English (auto-translated)"] = abstract_en

                preferred_langs = [
                    "English",
                    "English (auto-translated)",
                    "Hungarian",
                    "German",
                    "French",
                    "Spanish",
                    "Chinese",
                    "Russian",
                ]
                tab_labels: list[str] = []
                tab_contents: list[Any] = []

                for lang in preferred_langs:
                    if lang in available_abstracts:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])

                for lang in sorted(available_abstracts.keys()):
                    if lang not in preferred_langs:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])

                if "English" not in available_abstracts and "English (auto-translated)" not in available_abstracts:
                    tab_labels.append("English (auto-translated)")
                    tab_contents.append(None)

                if "Hungarian" not in available_abstracts:
                    tab_labels.append("Hungarian (auto-translated)")
                    tab_contents.append(None)

                if tab_labels:
                    tabs = st.tabs(tab_labels)
                    for tab_index, (tab, content) in enumerate(zip(tabs, tab_contents)):
                        with tab:
                            tab_label = tab_labels[tab_index]
                            if content is not None:
                                st.markdown(
                                    f'<div class="abstract-box">{html.escape(content)}</div>',
                                    unsafe_allow_html=True,
                                )
                                continue

                            target_language = "English" if "English" in tab_label else "Hungarian"
                            prefer_order = [
                                "English",
                                "German",
                                "French",
                                "Spanish",
                                "Chinese",
                                "Russian",
                                "Japanese",
                                "Korean",
                            ]
                            source_language = None
                            source_abstract = None
                            for lang in prefer_order:
                                if lang in available_abstracts and lang != target_language:
                                    source_language = lang
                                    source_abstract = available_abstracts[lang]
                                    break
                            if not source_abstract and available_abstracts:
                                for lang, txt in available_abstracts.items():
                                    if lang != target_language and txt:
                                        source_language = lang
                                        source_abstract = txt
                                        break

                            if not (source_abstract and source_language):
                                st.info(f"No abstract available for translation to {target_language}.")
                                continue

                            # Check disk cache first!
                            cached_text = get_cached_translation(
                                translation_cache,
                                assessment.record_id,
                                source_language,
                                target_language,
                            )
                            if cached_text:
                                st.markdown(
                                    f'<div class="abstract-box">{html.escape(cached_text)}</div>',
                                    unsafe_allow_html=True,
                                )
                            elif api_key:
                                if st.button(
                                    f"Translate to {target_language}",
                                    key=f"translate_btn_{assessment.record_id}_{target_language}",
                                ):
                                    try:
                                        with st.spinner(
                                            f"Translating from {source_language} to {target_language}..."
                                        ):
                                            translated = translate_text(
                                                source_abstract,
                                                source_language,
                                                target_language,
                                                api_key,
                                                model=trans_model,
                                                thinking_level=trans_thinking,
                                            )
                                        set_cached_translation(
                                            translation_cache,
                                            assessment.record_id,
                                            source_language,
                                            target_language,
                                            translated,
                                            model=trans_model,
                                            original_text=source_abstract,
                                        )
                                        st.rerun()
                                    except Exception as exc:
                                        st.error(f"Translation failed: {exc}")
                            else:
                                st.warning("GEMINI_API_KEY not configured. Cannot translate abstract.")
            else:
                primary_abstract_text = str(abstract_data)
                st.info(primary_abstract_text)
        else:
            st.info("No abstract available")

        # --- CLAIMS EXPANDER ---
        claims_text = _extract_claims_text(patent_data)
        if claims_text:
            with st.expander("Claims"):
                st.text(claims_text)

        # --- DEEP TECHNICAL BRIEF (FULL-TEXT OR UPLOADED PDF) ---
        st.markdown("#### Deep Technical Brief")

        # Direct links to fetch the full patent PDF
        gp_id = f"{assessment.jurisdiction}{assessment.doc_number}".replace(" ", "")
        google_patents_url = f"https://patents.google.com/patent/{gp_id}" if gp_id else None
        link_parts = []
        if provider_url:
            link_parts.append(f"[Open on Provider]({provider_url})")
        if google_patents_url:
            link_parts.append(f"[Open on Google Patents (PDF)]({google_patents_url})")
        if link_parts:
            st.caption("Full patent links: " + " · ".join(link_parts))

        # Stored PDF status, auto-fetch from Google Patents, & uploader
        stored_pdf = load_patent_pdf(assessment.record_id)
        if stored_pdf is not None:
            pdf_col1, pdf_col2, pdf_col3 = st.columns(
                [2.2, 1.3, 1.1], vertical_alignment="center"
            )
            with pdf_col1:
                st.success(f"Stored PDF attached ({len(stored_pdf) / 1024:.0f} KB)")
            with pdf_col2:
                st.download_button(
                    "Download PDF",
                    data=stored_pdf,
                    file_name=f"{assessment.jurisdiction}_{assessment.doc_number}.pdf",
                    mime="application/pdf",
                    key=f"dl_pdf_{assessment.record_id}",
                    width="stretch",
                )
            with pdf_col3:
                if st.button("Remove PDF", key=f"rm_pdf_{assessment.record_id}", width="stretch"):
                    delete_patent_pdf(assessment.record_id)
                    st.rerun()
        else:
            if gp_id and st.button(
                "Auto-fetch PDF from Google Patents",
                key=f"fetch_gp_pdf_{assessment.record_id}",
            ):
                with st.spinner(f"Downloading PDF for {gp_id} from Google Patents..."):
                    fetched_pdf = fetch_google_patents_pdf(
                        assessment.jurisdiction, assessment.doc_number
                    )
                if fetched_pdf:
                    save_patent_pdf(assessment.record_id, fetched_pdf)
                    st.success(f"Downloaded & saved PDF ({len(fetched_pdf) / 1024:.0f} KB).")
                    st.rerun()
                else:
                    st.warning(
                        "PDF not found automatically on Google Patents. "
                        "You can open the link above and upload it manually below."
                    )

            uploaded_pdf = st.file_uploader(
                "Or upload full patent PDF manually (saved for this patent)",
                type=["pdf"],
                key=f"upload_pdf_{assessment.record_id}",
            )
            if uploaded_pdf is not None:
                save_patent_pdf(assessment.record_id, uploaded_pdf.getvalue())
                st.success("Patent PDF saved.")
                st.rerun()

        brief_col1, brief_col2, _brief_col3 = st.columns(
            [1.4, 2.2, 1.4], vertical_alignment="bottom"
        )
        with brief_col1:
            brief_lang = st.selectbox(
                "Brief language",
                ["English", "Hungarian"],
                key=f"brief_lang_{assessment.record_id}",
            )
        brief_cache_id = f"{assessment.record_id}_brief"
        cached_brief = get_cached_translation(
            translation_cache, brief_cache_id, "patent", brief_lang
        )
        with brief_col2:
            btn_label = "Regenerate Brief" if cached_brief else "Generate Technical Brief"
            if stored_pdf is not None:
                btn_label += " (from PDF)"
            gen_brief_clicked = st.button(
                btn_label,
                key=f"gen_brief_{assessment.record_id}_{brief_lang}",
            )

        if gen_brief_clicked:
            if not api_key:
                st.warning("GEMINI_API_KEY not configured.")
            else:
                brief_model = st.session_state.get("llm_brief_model", config.llm_brief_model)
                brief_thinking = st.session_state.get(
                    "llm_brief_thinking_level", config.llm_brief_thinking_level
                )
                full_description = _extract_text_field(patent_data.get("description"))
                full_claims = claims_text

                # If no PDF is stored, attempt on-demand full-text fetch from Lens
                if stored_pdf is None and not full_description and assessment.lens_id and config.is_lens_configured:
                    try:
                        with st.spinner("Fetching full patent text from Lens.org..."):
                            full_rec = asyncio.run(
                                LensConnector().get_patent_by_lens_id(
                                    assessment.lens_id, include_full_text=True
                                )
                            )
                        if full_rec:
                            full_description = _extract_text_field(full_rec.get("description"))
                            fetched_claims = _extract_text_field(full_rec.get("claims"))
                            if fetched_claims:
                                full_claims = fetched_claims
                    except Exception as exc:
                        st.warning(f"Could not fetch full text from Lens ({exc}); using available text.")

                try:
                    source_desc = "stored PDF" if stored_pdf is not None else "patent text"
                    with st.spinner(
                        f"Generating {brief_lang} technical brief from {source_desc} ({brief_model}, {brief_thinking})..."
                    ):
                        brief_md = generate_technical_brief(
                            title=english_title or assessment.title,
                            abstract=primary_abstract_text,
                            description=full_description,
                            claims=full_claims,
                            pdf_bytes=stored_pdf,
                            jurisdiction=assessment.jurisdiction,
                            status_summary=assessment.status_analysis.interpretation,
                            classifications=getattr(assessment, "all_classifications", [])
                            or assessment.classification_tags,
                            output_language=brief_lang,
                            api_key=api_key,
                            model=brief_model,
                            thinking_level=brief_thinking,
                        )
                    set_cached_translation(
                        translation_cache,
                        brief_cache_id,
                        "patent",
                        brief_lang,
                        brief_md,
                        model=brief_model,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Brief generation failed: {exc}")

        if cached_brief:
            st.markdown(cached_brief)
        else:
            st.caption(
                "Upload the patent PDF above (recommended — includes figures, tables & full specification) "
                "or click Generate to fetch full text automatically when available."
            )

    with col2:
        # --- AI ANALYSIS (SEPARATE FROM GEORGE'S REVIEW) ---
        st.markdown("#### AI Analysis")
        st.progress(assessment.relevance_score / 100, text=f"AI Score: {assessment.relevance_score:.1f}/100")

        if getattr(assessment, "rationale", ""):
            st.markdown(f"**Rationale:** {assessment.rationale}")

        all_cls = getattr(assessment, "all_classifications", None) or assessment.classification_tags
        if all_cls:
            st.markdown("**IPC/CPC:** " + ", ".join(f"`{c}`" for c in all_cls[:12]))

        st.markdown("**LLM Tags**")
        if getattr(assessment, "llm_tags", None):
            pills = "".join(
                f'<span class="tag-pill">{html.escape(tag)}</span>'
                for tag in assessment.llm_tags
            )
            st.markdown(f'<div class="tag-container">{pills}</div>', unsafe_allow_html=True)
        else:
            st.caption("No tags")

        st.markdown("**Notable Features**")
        if getattr(assessment, "llm_features", None):
            for feature in assessment.llm_features:
                st.markdown(f"- {feature}")
        else:
            st.caption("None detected")

        st.markdown("---")

        # --- LEGAL STATUS ---
        if getattr(assessment, "status_analysis", None):
            status = assessment.status_analysis
            st.markdown("#### Legal Status")
            status_flags = []
            if status.is_refused:
                status_flags.append("🔴 Refused")
            if status.is_withdrawn:
                status_flags.append("⚠️ Withdrawn")
            if status.is_lapsed:
                status_flags.append("📉 Lapsed")
            if status.is_expired:
                status_flags.append("⏰ Expired")
            if status.is_inactive:
                status_flags.append("⏸️ Inactive")
            if status.is_active:
                status_flags.append("✅ Active")
            if status.is_pending:
                status_flags.append("⏳ Pending")

            if status_flags:
                st.markdown(f"**Status:** {' • '.join(status_flags)}")
            st.markdown(f"**Jurisdiction:** {status.jurisdiction}")
            if status.code_found:
                st.markdown(f"**Event Code:** `{status.code_found}`")

        st.markdown("---")

        # --- GEORGE'S REVIEW FORM ---
        st.markdown("#### George's Review")
        existing_review = get_review(assessment.record_id)
        if existing_review is not None:
            st.success(f"Saved Grade: **{existing_review['user_score']:.0f}/100**")
            default_user_score = round(float(existing_review["user_score"]))
            default_notes = existing_review.get("notes", "")
            default_cal = bool(existing_review.get("use_for_calibration", 1))
        else:
            st.caption("Not yet reviewed.")
            default_user_score = 50
            default_notes = ""
            default_cal = True

        user_score = st.slider(
            "My Score (0–100)",
            0,
            100,
            default_user_score,
            key=f"review_score_{assessment.record_id}",
        )
        review_notes = st.text_area(
            "Review Notes",
            value=default_notes,
            placeholder="e.g., EDM wire-bonding noise, or interesting H2 plasma cathode...",
            height=90,
            key=f"review_notes_{assessment.record_id}",
        )
        use_for_cal = st.checkbox(
            "Use as calibration example for LLM scoring",
            value=default_cal,
            key=f"review_cal_{assessment.record_id}",
        )

        rcol1, rcol2 = st.columns(2)
        with rcol1:
            if st.button("Save Review", key=f"save_rev_{assessment.record_id}", type="primary", width="stretch"):
                save_review(
                    record_id=assessment.record_id,
                    user_score=user_score,
                    notes=review_notes,
                    doc_number=assessment.doc_number,
                    jurisdiction=assessment.jurisdiction,
                    title=assessment.title,
                    title_en=english_title or "",
                    abstract=primary_abstract_text,
                    provider_name=assessment.provider_name,
                    provider_record_url=provider_url,
                    llm_score=assessment.relevance_score,
                    use_for_calibration=use_for_cal,
                )
                st.success("Review saved.")
                st.rerun()
        with rcol2:
            if existing_review is not None and st.button(
                "Delete", key=f"del_rev_{assessment.record_id}", width="stretch"
            ):
                delete_review(assessment.record_id)
                st.warning("Review deleted.")
                st.rerun()


def render_deep_dive_tab(assessments) -> None:
    if not assessments:
        st.info("No analysis data available yet.")
        return

    sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)
    available_record_ids = [a.record_id for a in sorted_assessments]

    selected_from_results = st.session_state.get("selected_record_id_for_analysis")
    if selected_from_results and selected_from_results in available_record_ids:
        current_idx = available_record_ids.index(selected_from_results)
    else:
        current_idx = 0

    nav1, nav2, nav3 = st.columns([1.0, 4.2, 1.0], vertical_alignment="center")
    with nav1:
        if st.button("◀ Prev", disabled=current_idx <= 0, width="stretch"):
            st.session_state["selected_record_id_for_analysis"] = available_record_ids[current_idx - 1]
            st.rerun()
    with nav2:
        selected_record_id = st.selectbox(
            "Select Patent",
            options=available_record_ids,
            index=current_idx,
            format_func=lambda x: next(
                (
                    f"[{a.relevance_score:.0f}] {a.jurisdiction} {a.doc_number} — {a.title_en or a.title or 'Untitled'}"
                    for a in sorted_assessments
                    if a.record_id == x
                ),
                x,
            ),
            label_visibility="collapsed",
            key="analysis_record_selector",
        )
        if selected_record_id != available_record_ids[current_idx]:
            st.session_state["selected_record_id_for_analysis"] = selected_record_id
            current_idx = available_record_ids.index(selected_record_id)
    with nav3:
        if st.button("Next ▶", disabled=current_idx >= len(available_record_ids) - 1, width="stretch"):
            st.session_state["selected_record_id_for_analysis"] = available_record_ids[current_idx + 1]
            st.rerun()

    target = next((a for a in sorted_assessments if a.record_id == selected_record_id), None)
    if target:
        render_deep_dive(target)
