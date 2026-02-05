import streamlit as st


def render_deep_dive(assessment):
    """Render a detailed view of a patent assessment."""

    # Header logic
    color = "#94A3B8"
    if assessment.intelligence_value == "HIGH":
        color = "#EF4444"
    elif assessment.intelligence_value == "MEDIUM":
        color = "#F59E0B"

    # Generate Lens.org link
    lens_url = f"https://www.lens.org/lens/patent/{assessment.lens_id}/frontpage"

    st.markdown(
        f"""
    <div class="glass-card" style="border-top: 4px solid {color}">
        <h2>{assessment.title}</h2>
        <p style="font-family: monospace; color: {color}; font-size: 1.2rem;">
            {assessment.lens_id} | {assessment.jurisdiction} | {assessment.doc_number}
        </p>
        <p style="margin-top: 10px;">
            <a href="{lens_url}" target="_blank" style="color: #00B4D8; text-decoration: none;">
                🔗 View on Lens.org
            </a>
        </p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### Abstract")
        patent_data = next(
            (p for p in st.session_state.get("all_raw_results", []) if p.get("lens_id") == assessment.lens_id),
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

                # List of preferred languages to show
                preferred_langs = ["English", "Hungarian", "French", "German", "Spanish", "Chinese", "Russian"]

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

                # Create tabs for available languages
                if tab_labels:
                    tabs = st.tabs(tab_labels)
                    for tab, content in zip(tabs, tab_contents):
                        with tab:
                            st.info(content)
                else:
                    st.info("No abstract available")
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
            "Based on keyword matching in title, abstract, and claims, combined with context analysis."
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

        # Tags section with icon and tooltip
        tags_tooltip = (
            "Classification tags identify key technical domains and subject areas covered by the patent. "
            "These help categorize and filter related technologies."
        )
        st.markdown(
            f"""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 20px; margin-bottom: 5px;">
            <strong>Tags</strong>
            <span style="cursor: help; color: #94A3B8;" title="{tags_tooltip}">?</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if assessment.classification_tags:
            for tag in assessment.classification_tags:
                st.markdown(f"`{tag}`")
        else:
            st.caption("No specific tags")

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
        if assessment.is_anomalous:
            st.markdown("`Heat signature detected`")
        else:
            st.caption("None detected")


def render_deep_dive_tab(assessments):
    st.markdown("### Detailed Analysis")

    if not assessments:
        st.info("No analysis data available yet.")
        return

    # Check if a specific lens ID was selected from the results tab
    selected_lens_id_from_results = st.session_state.get("selected_lens_id_for_analysis")

    # Determine which lens ID to display
    available_lens_ids = [a.lens_id for a in assessments]

    # If a lens ID was set from results tab selection, use it; otherwise use the first one
    if selected_lens_id_from_results and selected_lens_id_from_results in available_lens_ids:
        default_index = available_lens_ids.index(selected_lens_id_from_results)
        # Clear the session state after using it
        st.session_state["selected_lens_id_for_analysis"] = None
    else:
        default_index = 0

    # Selector
    selected_lens_id = st.selectbox(
        "Select Target for Analysis",
        options=available_lens_ids,
        index=default_index,
        format_func=lambda x: f"{x} - {next((a.title for a in assessments if a.lens_id == x), 'Unknown')}",
    )

    # Find selected assessment
    target = next((a for a in assessments if a.lens_id == selected_lens_id), None)

    if target:
        render_deep_dive(target)
