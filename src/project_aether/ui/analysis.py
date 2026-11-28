"""
Detailed Analysis tab: inspect patent metadata, auto-triggered Hungarian/English
translation (disk-cached), 3-button PDF Deep Technical Brief, 0-100 review form,
and keyboard shortcuts.
"""

from __future__ import annotations

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


def _inject_keyboard_shortcuts() -> None:
    """Bind Left/Right navigation, 0-9 score shortcuts, Enter/Ctrl+S save, and direct PDF upload trigger."""
    st.iframe(
        """
<script>
(function() {
  const doc = window.parent.document;
  if (doc.__aetherShortcutsHandler) {
    doc.removeEventListener('keydown', doc.__aetherShortcutsHandler, true);
  }
  if (doc.__aetherClickHandler) {
    doc.removeEventListener('click', doc.__aetherClickHandler, true);
  }

  function findButtonByText(patterns) {
    const buttons = Array.from(doc.querySelectorAll('button'));
    for (const btn of buttons) {
      if (btn.disabled) continue;
      const txt = (btn.innerText || '').trim();
      for (const pat of patterns) {
        if (txt === pat || txt.includes(pat)) return btn;
      }
    }
    return null;
  }

  function setScoreSlider(scoreValue) {
    const sliders = Array.from(doc.querySelectorAll('[role="slider"]'));
    const targetSlider = sliders.find(
      (el) => (el.getAttribute('aria-label') || '').includes('My Score')
    );
    if (!targetSlider) return;
    targetSlider.focus();
    const fireKey = (key, code, keyCode) => {
      targetSlider.dispatchEvent(new KeyboardEvent('keydown', {
        key, code, keyCode, which: keyCode, bubbles: true, cancelable: true
      }));
    };
    fireKey('Home', 'Home', 36);
    for (let i = 0; i < scoreValue; i++) {
      fireKey('ArrowRight', 'ArrowRight', 39);
    }
  }

  function focusReviewNotes() {
    const ta = doc.querySelector('textarea[aria-label="Review Notes"]');
    if (ta) {
      ta.focus();
      ta.setSelectionRange(ta.value.length, ta.value.length);
    }
  }

  // Direct OS file dialog trigger for "Upload PDF" / "Replace PDF" button
  const clickHandler = function(e) {
    const btn = e.target.closest ? e.target.closest('button') : null;
    if (!btn) return;
    const txt = (btn.innerText || '').trim();
    if (txt === 'Upload PDF' || txt === 'Replace PDF') {
      const pdfInput = doc.querySelector('.st-key-aether_hidden_pdf_uploader_wrap input[type="file"]');
      if (pdfInput) {
        e.preventDefault();
        e.stopPropagation();
        pdfInput.click();
      }
    }
  };

  const handler = function(e) {
    const active = doc.activeElement;
    const tag = active ? active.tagName.toLowerCase() : '';
    const isReviewNotes = tag === 'textarea' && (active.getAttribute('aria-label') || '') === 'Review Notes';
    const isTyping = tag === 'input' || tag === 'textarea' || tag === 'select' || (active && active.isContentEditable);

    // Inside Review Notes: Enter (without Shift) or Ctrl+S saves; Shift+Enter inserts newline
    if (isReviewNotes) {
      const isPlainEnter = e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !e.altKey;
      const isCtrlS = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's';
      if (isPlainEnter || isCtrlS) {
        e.preventDefault();
        e.stopPropagation();
        active.blur();
        setTimeout(() => {
          const saveBtn = findButtonByText(['Save Review', 'Update Review']);
          if (saveBtn) saveBtn.click();
        }, 60);
      }
      return;
    }

    if (isTyping) return;

    // Left / Right arrow keys -> Prev / Next patent
    if (e.key === 'ArrowLeft') {
      const prevBtn = findButtonByText(['Prev']);
      if (prevBtn) {
        e.preventDefault();
        prevBtn.click();
      }
      return;
    }
    if (e.key === 'ArrowRight') {
      const nextBtn = findButtonByText(['Next']);
      if (nextBtn) {
        e.preventDefault();
        nextBtn.click();
      }
      return;
    }

    // Numeric keys 0-9 -> set score (0->0, 1->10, ..., 9->90) and focus Review Notes
    if (!e.ctrlKey && !e.metaKey && !e.altKey && /^[0-9]$/.test(e.key)) {
      e.preventDefault();
      const score = parseInt(e.key, 10) * 10;
      setScoreSlider(score);
      setTimeout(focusReviewNotes, 100);
    }
  };

  doc.__aetherShortcutsHandler = handler;
  doc.__aetherClickHandler = clickHandler;
  doc.addEventListener('keydown', handler, true);
  doc.addEventListener('click', clickHandler, true);
})();
</script>
""",
        height=1,
    )


def render_deep_dive(assessment) -> None:
    """Render a detailed architectural dossier of a patent assessment."""
    config = get_config()
    api_key = config.google_api_key or os.getenv("GEMINI_API_KEY", "")

    accent_color = "#64748B"
    if assessment.intelligence_value == "HIGH":
        accent_color = "#DC2626"
    elif assessment.intelligence_value == "MEDIUM":
        accent_color = "#D97706"

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
    subtitle_html = ""
    if english_title and english_title.strip().lower() != (assessment.title or "").strip().lower():
        subtitle_html = f'<p class="aether-dossier-subtitle">{html.escape(english_title)}</p>'

    inventors_str = ", ".join(assessment.inventors) if assessment.inventors else "Unknown"
    applicants = getattr(assessment, "applicants", None) or []
    applicants_str = ", ".join(applicants) if applicants else "Not listed"
    pub_date = getattr(assessment, "date_published", None) or patent_data.get("date_published") or "Unknown"
    domain_cat = getattr(assessment, "domain_category", "") or ""
    doc_ref = f"{assessment.jurisdiction} {assessment.doc_number}".strip()

    domain_meta = (
        f'<span class="aether-meta-item"><span class="aether-meta-key">Domain</span>'
        f'<span class="aether-meta-val">{html.escape(domain_cat)}</span></span>'
        if domain_cat
        else ""
    )

    links_parts = []
    if provider_url:
        links_parts.append(
            f'<a href="{html.escape(provider_url)}" target="_blank" class="aether-link">Open provider record ↗</a>'
        )
    if legal_history_url:
        links_parts.append(
            f'<a href="{html.escape(legal_history_url)}" target="_blank" class="aether-link">Legal history ↗</a>'
        )
    links_html = (
        f'<div class="aether-links-row">{"".join(links_parts)}</div>'
        if links_parts
        else ""
    )

    header_html = (
        f'<div class="aether-dossier-header" style="--card-accent: {accent_color};">'
        f'<div class="aether-dossier-title">{safe_title}</div>'
        f"{subtitle_html}"
        f'<div class="aether-meta-grid">'
        f'<span class="aether-meta-item"><span class="aether-meta-key">Document</span><span class="aether-meta-val aether-mono">{html.escape(doc_ref)}</span></span>'
        f'<span class="aether-meta-item"><span class="aether-meta-key">Record ID</span><span class="aether-meta-val aether-mono">{html.escape(assessment.record_id)}</span></span>'
        f'<span class="aether-meta-item"><span class="aether-meta-key">Published</span><span class="aether-meta-val">{html.escape(str(pub_date))}</span></span>'
        f"{domain_meta}"
        f'<span class="aether-meta-item"><span class="aether-meta-key">Inventors</span><span class="aether-meta-val">{html.escape(inventors_str)}</span></span>'
        f'<span class="aether-meta-item"><span class="aether-meta-key">Applicants</span><span class="aether-meta-val">{html.escape(applicants_str)}</span></span>'
        f"</div>"
        f"{links_html}"
        f"</div>"
    )
    st.markdown(header_html, unsafe_allow_html=True)

    col1, col2 = st.columns([2.1, 1], gap="large")

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
                for lang in preferred_langs:
                    if lang in available_abstracts:
                        tab_labels.append(lang)
                for lang in sorted(available_abstracts.keys()):
                    if lang not in preferred_langs:
                        tab_labels.append(lang)

                if "English" not in available_abstracts and "English (auto-translated)" not in available_abstracts:
                    tab_labels.append("English (auto-translated)")
                if "Hungarian" not in available_abstracts:
                    tab_labels.append("Hungarian (auto-translated)")

                if tab_labels:
                    selected_abs_tab = st.segmented_control(
                        "Abstract language",
                        options=tab_labels,
                        default=tab_labels[0],
                        key=f"abs_lang_tab_{assessment.record_id}",
                        label_visibility="collapsed",
                    ) or tab_labels[0]

                    if selected_abs_tab in available_abstracts:
                        st.markdown(
                            f'<div class="aether-abstract">{html.escape(available_abstracts[selected_abs_tab])}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        target_language = "English" if "English" in selected_abs_tab else "Hungarian"
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
                        else:
                            cached_text = get_cached_translation(
                                translation_cache,
                                assessment.record_id,
                                source_language,
                                target_language,
                            )
                            if cached_text:
                                st.markdown(
                                    f'<div class="aether-abstract">{html.escape(cached_text)}</div>',
                                    unsafe_allow_html=True,
                                )
                            elif api_key:
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
                                    st.markdown(
                                        f'<div class="aether-abstract">{html.escape(translated)}</div>',
                                        unsafe_allow_html=True,
                                    )
                                except Exception as exc:
                                    st.error(f"Translation failed: {exc}")
                            else:
                                st.warning("GEMINI_API_KEY not configured. Cannot translate abstract.")
            else:
                primary_abstract_text = str(abstract_data)
                st.markdown(
                    f'<div class="aether-abstract">{html.escape(primary_abstract_text)}</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No abstract available for this patent.")

        # --- CLAIMS EXPANDER ---
        claims_text = _extract_claims_text(patent_data)
        if claims_text:
            with st.expander("Claims"):
                st.text(claims_text)

        # --- DEEP TECHNICAL BRIEF (3-BUTTON SINGLE-LINE LAYOUT, ENGLISH ONLY) ---
        st.markdown("#### Deep technical brief")

        gp_id = f"{assessment.jurisdiction}{assessment.doc_number}".replace(" ", "")
        google_patents_url = f"https://patents.google.com/patent/{gp_id}" if gp_id else None
        stored_pdf = load_patent_pdf(assessment.record_id)
        brief_cache_id = f"{assessment.record_id}_brief"
        cached_brief = get_cached_translation(
            translation_cache, brief_cache_id, "patent", "English"
        )

        bcol1, bcol2, bcol3 = st.columns(3, vertical_alignment="center")
        with bcol1:
            if stored_pdf is not None:
                if st.button(
                    "Remove PDF",
                    key=f"rm_pdf_{assessment.record_id}",
                    width="stretch",
                ):
                    delete_patent_pdf(assessment.record_id)
                    st.rerun()
            else:
                if st.button(
                    "Auto-fetch PDF",
                    key=f"fetch_gp_pdf_{assessment.record_id}",
                    disabled=not bool(google_patents_url),
                    width="stretch",
                ):
                    with st.spinner(""):
                        fetched_pdf = fetch_google_patents_pdf(
                            assessment.jurisdiction, assessment.doc_number
                        )
                    if fetched_pdf:
                        save_patent_pdf(assessment.record_id, fetched_pdf)
                        st.rerun()
                    else:
                        st.warning("PDF not available automatically on Google Patents.")
        with bcol2:
            upload_label = "Replace PDF" if stored_pdf is not None else "Upload PDF"
            st.button(
                upload_label,
                key=f"trigger_upload_pdf_{assessment.record_id}",
                width="stretch",
            )
        with bcol3:
            gen_brief_clicked = st.button(
                "Generate Technical Brief",
                key=f"gen_brief_{assessment.record_id}",
                disabled=stored_pdf is None,
                width="stretch",
            )

        # Hidden file uploader triggered directly by the "Upload PDF" / "Replace PDF" button
        with st.container(key="aether_hidden_pdf_uploader_wrap"):
            st.markdown('<div class="aether-hidden-pdf-uploader">', unsafe_allow_html=True)
            uploaded_pdf = st.file_uploader(
                "PDF",
                type=["pdf"],
                key=f"upload_pdf_{assessment.record_id}",
                label_visibility="collapsed",
            )
            st.markdown("</div>", unsafe_allow_html=True)
            if uploaded_pdf is not None:
                save_patent_pdf(assessment.record_id, uploaded_pdf.getvalue())
                st.rerun()

        if gen_brief_clicked and stored_pdf is not None:
            if not api_key:
                st.warning("GEMINI_API_KEY not configured.")
            else:
                brief_model = st.session_state.get("llm_brief_model", config.llm_brief_model)
                brief_thinking = st.session_state.get(
                    "llm_brief_thinking_level", config.llm_brief_thinking_level
                )
                try:
                    with st.spinner(f"Generating English technical brief from PDF ({brief_model}, {brief_thinking})..."):
                        brief_md = generate_technical_brief(
                            title=english_title or assessment.title,
                            abstract=primary_abstract_text,
                            claims=claims_text,
                            pdf_bytes=stored_pdf,
                            jurisdiction=assessment.jurisdiction,
                            status_summary=assessment.status_analysis.interpretation,
                            classifications=getattr(assessment, "all_classifications", [])
                            or assessment.classification_tags,
                            output_language="English",
                            api_key=api_key,
                            model=brief_model,
                            thinking_level=brief_thinking,
                        )
                    set_cached_translation(
                        translation_cache,
                        brief_cache_id,
                        "patent",
                        "English",
                        brief_md,
                        model=brief_model,
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Brief generation failed: {exc}")

        if cached_brief:
            st.markdown(cached_brief)
        else:
            st.markdown(
                '<div class="aether-abstract aether-abstract--muted">'
                "Attach a patent PDF using <strong>Auto-fetch PDF</strong> or <strong>Upload PDF</strong> above to generate a deep technical brief."
                "</div>",
                unsafe_allow_html=True,
            )

    with col2:
        # --- RELEVANCE ANALYSIS ---
        st.markdown("#### Relevance analysis")
        st.progress(assessment.relevance_score / 100, text=f"Score: {assessment.relevance_score:.1f} / 100")

        if getattr(assessment, "rationale", ""):
            st.markdown(f"**Rationale:** {assessment.rationale}")

        all_cls = getattr(assessment, "all_classifications", None) or assessment.classification_tags
        if all_cls:
            st.markdown("**IPC/CPC:** " + ", ".join(f"`{c}`" for c in all_cls[:12]))

        st.markdown("**Tags**")
        if getattr(assessment, "llm_tags", None):
            tag_items = '<span class="aether-tag-sep">·</span>'.join(
                html.escape(tag) for tag in assessment.llm_tags
            )
            st.markdown(f'<div class="aether-tag-list">{tag_items}</div>', unsafe_allow_html=True)
        else:
            st.caption("No tags recorded.")

        st.markdown("**Notable features**")
        if getattr(assessment, "llm_features", None):
            for feature in assessment.llm_features:
                st.markdown(f"- {feature}")
        else:
            st.caption("None detected.")

        st.markdown("---")

        # --- LEGAL STATUS ---
        if getattr(assessment, "status_analysis", None):
            status = assessment.status_analysis
            st.markdown("#### Legal status")
            status_flags = []
            if status.is_refused:
                status_flags.append(("aether-dot--err", "Refused"))
            if status.is_withdrawn:
                status_flags.append(("aether-dot--warn", "Withdrawn"))
            if status.is_lapsed:
                status_flags.append(("aether-dot--warn", "Lapsed"))
            if status.is_expired:
                status_flags.append(("aether-dot--muted", "Expired"))
            if status.is_inactive:
                status_flags.append(("aether-dot--muted", "Inactive"))
            if status.is_active:
                status_flags.append(("aether-dot--ok", "Active"))
            if status.is_pending:
                status_flags.append(("aether-dot--warn", "Pending"))

            if status_flags:
                flags_html = "".join(
                    f'<span class="aether-inline-status"><span class="aether-dot {dot}"></span>{lbl}</span>'
                    for dot, lbl in status_flags
                )
                st.markdown(f'<div style="margin-bottom: 0.45rem;">{flags_html}</div>', unsafe_allow_html=True)
            st.markdown(f"**Jurisdiction:** {status.jurisdiction}")
            if status.code_found:
                st.markdown(f"**Event code:** `{status.code_found}`")

        st.markdown("---")

        # --- REVIEW FORM ---
        st.markdown("#### Reviewer assessment")
        existing_review = get_review(assessment.record_id)
        score_key = f"review_score_{assessment.record_id}"
        notes_key = f"review_notes_{assessment.record_id}"
        cal_key = f"review_cal_{assessment.record_id}"

        if existing_review is not None:
            st.success(f"Saved grade: **{existing_review['user_score']:.0f} / 100**")
            default_user_score = round(float(existing_review["user_score"]))
            default_notes = existing_review.get("notes", "")
            default_cal = bool(existing_review.get("use_for_calibration", 1))
        else:
            st.caption("Keys 0-9 set score (0-90) and focus notes · Enter or Ctrl+S saves · Left/Right switches patent.")
            default_user_score = 50
            default_notes = ""
            default_cal = True

        user_score = st.slider(
            "My Score (0-100)",
            0,
            100,
            default_user_score,
            key=score_key,
        )
        review_notes = st.text_area(
            "Review Notes",
            value=default_notes,
            placeholder="Enter to save, Shift+Enter for newline...",
            height=90,
            key=notes_key,
        )
        use_for_cal = st.checkbox(
            "Use to calibrate relevance scoring",
            value=default_cal,
            key=cal_key,
        )

        save_label = "Update Review" if existing_review is not None else "Save Review"
        rcol1, rcol2 = st.columns(2)
        with rcol1:
            if st.button(save_label, key=f"save_rev_{assessment.record_id}", type="primary", width="stretch"):
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
                "Delete Review", key=f"del_rev_{assessment.record_id}", width="stretch"
            ):
                delete_review(assessment.record_id)
                st.session_state.pop(score_key, None)
                st.session_state.pop(notes_key, None)
                st.session_state.pop(cal_key, None)
                st.warning("Review deleted.")
                st.rerun()

    _inject_keyboard_shortcuts()


def _select_patent(record_id: str) -> None:
    st.session_state["selected_record_id_for_analysis"] = record_id
    st.session_state["analysis_record_selector"] = record_id


def render_deep_dive_tab(assessments) -> None:
    if not assessments:
        st.info("No analysis data available yet. Run a search from the sidebar to inspect patents.")
        return

    sorted_assessments = sorted(assessments, key=lambda a: a.relevance_score, reverse=True)
    available_record_ids = [a.record_id for a in sorted_assessments]

    selected_from_results = st.session_state.get("selected_record_id_for_analysis")
    if selected_from_results and selected_from_results in available_record_ids:
        st.session_state["analysis_record_selector"] = selected_from_results
    elif st.session_state.get("analysis_record_selector") not in available_record_ids:
        st.session_state["analysis_record_selector"] = available_record_ids[0]

    current_id = st.session_state["analysis_record_selector"]
    current_idx = available_record_ids.index(current_id)

    nav1, nav2, nav3 = st.columns([0.9, 4.4, 0.9], vertical_alignment="center")
    with nav1:
        st.button(
            "Prev",
            disabled=current_idx <= 0,
            width="stretch",
            on_click=_select_patent,
            args=(available_record_ids[max(0, current_idx - 1)],),
        )
    with nav2:
        selected_record_id = st.selectbox(
            "Select Patent",
            options=available_record_ids,
            format_func=lambda x: next(
                (
                    f"[{a.relevance_score:.0f}] {a.jurisdiction} {a.doc_number} · {a.title_en or a.title or 'Untitled'}"
                    for a in sorted_assessments
                    if a.record_id == x
                ),
                x,
            ),
            label_visibility="collapsed",
            key="analysis_record_selector",
        )
        st.session_state["selected_record_id_for_analysis"] = selected_record_id
    with nav3:
        st.button(
            "Next",
            disabled=current_idx >= len(available_record_ids) - 1,
            width="stretch",
            on_click=_select_patent,
            args=(available_record_ids[min(len(available_record_ids) - 1, current_idx + 1)],),
        )

    target = next((a for a in sorted_assessments if a.record_id == selected_record_id), None)
    if target:
        render_deep_dive(target)
