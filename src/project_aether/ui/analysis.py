import streamlit as st
import os
from project_aether.core.translation_service import (
    translate_text,
    load_translation_cache,
    save_translation_cache,
    get_cached_translation,
    set_cached_translation,
)


def render_deep_dive(assessment):
    """Render a detailed view of a patent assessment."""

    # Header logic
    color = "#94A3B8"
    if assessment.intelligence_value == "HIGH":
        color = "#EF4444"
    elif assessment.intelligence_value == "MEDIUM":
        color = "#F59E0B"

    provider_url = assessment.provider_record_url
    
    # Get the original patent record to check for English translation
    patent_data = next(
        (
            p
            for p in st.session_state.get("all_raw_results", [])
            if p.get("record_id") == assessment.record_id
        ),
        {},
    )
    english_title = patent_data.get("title_en")
    
    # Build title section: show English translation in brackets if it exists
    title_html = f"<h2>{assessment.title}</h2>"
    if english_title:
        title_html += f"<p style=\"font-size: 0.95rem; color: #94A3B8; margin-top: -10px;\">({english_title})</p>"

    st.markdown(
        f"""
    <div class="glass-card" style="border-top: 4px solid {color}">
        {title_html}
        <p>by {assessment.inventors}</p>
        <p style="font-family: monospace; color: {color}; font-size: 1.2rem;">
            {assessment.record_id} | {assessment.jurisdiction} | {assessment.doc_number}
        </p>
        {
            f'<p style="margin-top: 10px;"><a href="{provider_url}" target="_blank" style="color: #00B4D8; text-decoration: none;">🔗 View on Provider</a></p>'
            if provider_url
            else '<p style="margin-top: 10px; color: #94A3B8;">No provider link available.</p>'
        }
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Abstract")
        patent_data = next(
            (
                p
                for p in st.session_state.get("all_raw_results", [])
                if p.get("record_id") == assessment.record_id
            ),
            {},
        )

        # Handle abstract with multiple languages
        abstract_data = patent_data.get("abstract", None)

        if abstract_data:
            # If abstract is a list of language objects
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
                }

                # Build dictionary of available languages
                available_abstracts = {}
                for abstract_obj in abstract_data:
                    lang_code = abstract_obj.get("lang", "unknown").lower()
                    lang_name = lang_map.get(lang_code, lang_code.upper())
                    available_abstracts[lang_name] = abstract_obj.get("text", "")

                # Check if abstract_en exists (auto-translated during search)
                abstract_en = patent_data.get("abstract_en")
                if abstract_en and "English" not in available_abstracts:
                    # Add auto-translated English abstract directly
                    available_abstracts["English (auto-translated)"] = abstract_en

                # List of preferred languages to show
                preferred_langs = ["English", "English (auto-translated)", "Hungarian", "French", "German", "Spanish", "Chinese", "Russian"]

                # Create tabs for available languages
                tab_labels = []
                tab_contents = []

                for lang in preferred_langs:
                    if lang in available_abstracts:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])

                # Add any other languages not in the preferred list
                for lang in sorted(available_abstracts.keys()):
                    if lang not in preferred_langs:
                        tab_labels.append(lang)
                        tab_contents.append(available_abstracts[lang])
                
                # Only add English auto-translation tab if English is not available and abstract_en doesn't exist
                # (This handles on-demand translation from other languages)
                if "English" not in available_abstracts and "English (auto-translated)" not in available_abstracts:
                    tab_labels.append("English (auto-translated)")
                    tab_contents.append(None)  # Placeholder for on-demand translation
                
                # Add Hungarian (auto-translated) tab if not already present in available abstracts
                if "Hungarian" not in available_abstracts:
                    tab_labels.append("Hungarian (auto-translated)")
                    tab_contents.append(None)  # Placeholder for auto-translated content

                # Create tabs for available languages
                if tab_labels:
                    tabs = st.tabs(tab_labels)
                    
                    for tab_index, (tab, content) in enumerate(zip(tabs, tab_contents)):
                        with tab:
                            # Determine which language this tab is for
                            tab_label = tab_labels[tab_index]
                            
                            # Handle auto-translated tabs (English and Hungarian)
                            if content is None:
                                # Determine target language based on tab label
                                if "English" in tab_label:
                                    target_language = "English"
                                    session_key_prefix = "english_translation"
                                elif "Hungarian" in tab_label:
                                    target_language = "Hungarian"
                                    session_key_prefix = "hungarian_translation"
                                else:
                                    # Should not happen
                                    st.info("Auto-translation not available for this language.")
                                    continue
                                
                                translation_key = f"{session_key_prefix}_{assessment.record_id}"
                                translated_content = st.session_state.get(translation_key, None)
                                
                                if translated_content is None:
                                    # Translation not yet requested/loaded
                                    # Find the first available abstract as source
                                    source_language = None
                                    source_abstract = None
                                    
                                    # Prefer languages in this order (avoid translating from target language)
                                    prefer_order = ["English", "French", "German", "Spanish", "Chinese", "Russian"]
                                    for lang in prefer_order:
                                        if lang in available_abstracts and lang != target_language:
                                            source_language = lang
                                            source_abstract = available_abstracts[lang]
                                            break
                                    
                                    if source_abstract and source_language:
                                        api_key = os.getenv("GEMINI_API_KEY")
                                        if api_key:
                                            if st.button(f"Translate to {target_language}", key=f"translate_btn_{assessment.record_id}_{target_language}"):
                                                # Load translation cache from disk
                                                translation_cache = load_translation_cache()
                                                
                                                try:
                                                    with st.spinner(f"Translating from {source_language} to {target_language}..."):
                                                        translated = translate_text(
                                                            source_abstract,
                                                            source_language,
                                                            target_language,
                                                            api_key
                                                        )
                                                    # Cache translation to both session state and disk
                                                    st.session_state[translation_key] = translated
                                                    set_cached_translation(
                                                        translation_cache,
                                                        assessment.record_id,
                                                        source_language,
                                                        target_language,
                                                        translated,
                                                        original_text=source_abstract
                                                    )
                                                    save_translation_cache(translation_cache)
                                                    st.rerun()
                                                except Exception as e:
                                                    st.error(f"Translation failed: {str(e)}")
                                        else:
                                            st.warning("GEMINI_API_KEY not configured. Cannot translate abstract.")
                                    else:
                                        st.info(f"No abstract available for translation to {target_language}.")
                                elif translated_content == "":
                                    # Translation was attempted but failed
                                    st.info("Translation not available.")
                                else:
                                    # Show cached translation
                                    st.info(translated_content)
                            else:
                                # Regular language tab
                                st.info(content)
            else:
                # If abstract is a simple string
                st.info(abstract_data)
        else:
            st.info("No abstract available")

    with col2:
        # Relevance section with tooltip
        st.markdown(
            """
        <div style="display: flex; align-items: center; gap: 8px;">
            <h4 style="margin: 0;">AI Analysis</h4>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Relevance score with icon and tooltip
        relevance_tooltip = (
            "Relevance score indicates how closely this patent matches the search criteria. "
            "Based on LLM scoring over the English title and abstract with keyword weighting."
        )
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 15px; margin-bottom: 10px;">
            <strong>Relevance</strong>
            <span style="cursor: help; color: #94A3B8;" title="{relevance_tooltip}">?</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
        st.progress(assessment.relevance_score / 100, text=f"{assessment.relevance_score:.1f}%")

        st.markdown(
            """
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px; margin-bottom: 5px;">
            <strong>LLM Tags</strong>
            <span style="cursor: help; color: #94A3B8;" title="Key terms extracted by the LLM from the title and abstract.">?</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if getattr(assessment, "llm_tags", None):
            for tag in assessment.llm_tags:
                st.markdown(f"`{tag}`")
        else:
            st.caption("No tags")

        # Notable Features section with icon and tooltip
        features_tooltip = (
            "Notable features highlight unusual or significant technical characteristics detected in the patent, "
            "such as anomalous energy patterns or heat signatures."
        )
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px; margin-bottom: 5px;">
            <strong>Notable Features</strong>
            <span style="cursor: help; color: #94A3B8;" title="{features_tooltip}">?</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if getattr(assessment, "llm_features", None):
            for feature in assessment.llm_features:
                st.markdown(f"- {feature}")
        else:
            st.caption("None detected")


def render_deep_dive_tab(assessments):
    if not assessments:
        st.info("No analysis data available yet.")
        return

    # Check if a specific record ID was selected from the results tab
    selected_record_id_from_results = st.session_state.get("selected_record_id_for_analysis")

    # Determine which record ID to display
    available_record_ids = [a.record_id for a in assessments]

    # If a record ID was set from results tab selection, use it; otherwise use the first one
    if selected_record_id_from_results and selected_record_id_from_results in available_record_ids:
        default_index = available_record_ids.index(selected_record_id_from_results)
        # Clear the session state after using it
        st.session_state["selected_record_id_for_analysis"] = None
    else:
        default_index = 0

    # Selector
    selected_record_id = st.selectbox(
        "Select Patent",
        options=available_record_ids,
        index=default_index,
        format_func=lambda x: f"{x} - {next((a.title for a in assessments if a.record_id == x), 'Unknown')}",
        label_visibility="collapsed",
    )

    # Find selected assessment
    target = next((a for a in assessments if a.record_id == selected_record_id), None)

    if target:
        render_deep_dive(target)
