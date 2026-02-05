from datetime import datetime

import streamlit as st

from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords, translation_context
from project_aether.core.keyword_translation import (
    load_keyword_cache,
    save_keyword_cache,
    ensure_keyword_set,
    get_cached_translation,
    set_cached_translation,
    keyword_set_id,
    default_translation_for_language,
    translate_keywords_with_llm,
    get_history_entries,
    delete_keyword_set,
)
from project_aether.core.keywords import DEFAULT_KEYWORDS


def load_keyword_set_callback(entry):
    """Callback to load keyword set into session state before widget rendering."""
    if "keyword_config" in st.session_state:
        st.session_state["keyword_config"].setdefault("English", {})["positive"] = entry.get("include", [])
        st.session_state["keyword_config"].setdefault("English", {})["negative"] = entry.get("exclude", [])

    # Increment widget version to force recreation
    st.session_state["keyword_widget_version"] = st.session_state.get("keyword_widget_version", 0) + 1


def render_sidebar(language_map):
    with st.sidebar:
        config = get_config()

        # Use infinite date window (no date filtering)
        end_date = datetime.now()
        start_date = None

        # Initialize language selection in session state
        if "selected_language" not in st.session_state:
            st.session_state.selected_language = "English"

        language_options = list(language_map.keys())
        selected_language_name = st.selectbox(
            "Language",
            options=language_options,
            index=language_options.index(st.session_state.selected_language),
            help="Language for the search query. The API will use this language for multi-lingual search.",
        )

        # Store selected language
        st.session_state.selected_language = selected_language_name
        selected_language_code = language_map[selected_language_name]

        # Jurisdiction is set to ALL by default (no filter)
        selected_jurisdictions = None

        keyword_config = st.session_state.get("keyword_config", DEFAULT_KEYWORDS)
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        cache = st.session_state.get("keyword_cache", {})
        widget_version = st.session_state.get("keyword_widget_version", 0)

        with st.expander("Current keyword set", expanded=True):
            set_label = st.text_input("Name (optional)", key="sidebar_set_label", placeholder="e.g. My Custom Keywords")

            include_text = st.text_area(
                "Include terms",
                value=", ".join(include_terms),
                height=120,
                key=f"sidebar_include_terms_{widget_version}",
            )
            exclude_text = st.text_area(
                "Exclude terms",
                value=", ".join(exclude_terms),
                height=120,
                key=f"sidebar_exclude_terms_{widget_version}",
            )

            updated_include = [term.strip() for term in include_text.split(",") if term.strip()]
            updated_exclude = [term.strip() for term in exclude_text.split(",") if term.strip()]
            keyword_config.setdefault("English", {})["positive"] = updated_include
            keyword_config.setdefault("English", {})["negative"] = updated_exclude
            st.session_state["keyword_config"] = keyword_config

            st.caption(f"Include: {len(updated_include)} terms | Exclude: {len(updated_exclude)} terms")

            if st.button("💾 Save", use_container_width=True):
                ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                save_keyword_cache(cache)
                st.session_state["keyword_cache"] = cache
                st.success("Keyword set saved to history")

        # Since jurisdiction is always ALL now, show translations for selected language if not English
        target_languages = [selected_language_name] if selected_language_name != "English" else []

        with st.expander("Translations", expanded=bool(target_languages)):
            if not target_languages:
                st.caption("No translations needed for English language selection.")
            else:
                if not config.google_api_key:
                    st.warning("LLM translation requires GOOGLE_API_KEY. Using cached or default translations only.")

                if st.button("Generate", use_container_width=True):
                    set_id = keyword_set_id(updated_include, updated_exclude)
                    for language in target_languages:
                        translation_successful = False
                        if config.google_api_key:
                            try:
                                translated_include, translated_exclude = translate_keywords_with_llm(
                                    include_terms=updated_include,
                                    exclude_terms=updated_exclude,
                                    target_language=language,
                                    context=translation_context(),
                                    api_key=config.google_api_key,
                                )
                                set_cached_translation(
                                    cache,
                                    set_id=set_id,
                                    language=language,
                                    include_terms=translated_include,
                                    exclude_terms=translated_exclude,
                                    source="llm",
                                )
                                translation_successful = True
                            except Exception as exc:
                                st.warning(f"Translation failed for {language}: {exc}")

                        if not translation_successful:
                            fallback = default_translation_for_language(language)
                            if fallback:
                                translated_include, translated_exclude = fallback
                                set_cached_translation(
                                    cache,
                                    set_id=set_id,
                                    language=language,
                                    include_terms=translated_include,
                                    exclude_terms=translated_exclude,
                                    source="default",
                                )
                    save_keyword_cache(cache)
                    st.session_state["keyword_cache"] = cache
                    st.success("Translations updated")

                set_id = keyword_set_id(updated_include, updated_exclude)
                for language in target_languages:
                    cached = get_cached_translation(cache, set_id, language)
                    if cached:
                        include_list = ", ".join(cached.get("include", []))
                        exclude_list = ", ".join(cached.get("exclude", []))
                        st.markdown(f"**{language}**")
                        st.caption(f"Include: {include_list}")
                        st.caption(f"Exclude: {exclude_list}")
                    else:
                        st.markdown(f"**{language}**")
                        st.caption("No cached translation yet.")

        with st.expander("Previous keyword sets"):
            history_entries = get_history_entries(cache)
            if not history_entries:
                st.caption("No saved keyword sets yet.")
            else:
                labels = [entry.get("label", entry["id"]) for entry in history_entries]
                selected_label = st.selectbox("Select a saved set", options=labels)
                selected_entry = next(
                    (entry for entry in history_entries if entry.get("label", entry["id"]) == selected_label),
                    history_entries[0],
                )
                col_load, col_delete = st.columns(2)
                with col_load:
                    if st.button("📂", use_container_width=True, on_click=load_keyword_set_callback, args=(selected_entry,)):
                        st.success("Keyword set loaded")
                        st.rerun()
                with col_delete:
                    if st.button("🗑️", use_container_width=True):
                        delete_keyword_set(cache, selected_entry["id"])
                        save_keyword_cache(cache)
                        st.session_state["keyword_cache"] = cache
                        st.success("Keyword set deleted")
                        st.rerun()

        st.markdown("---")

        col_btn, _ = st.columns([1, 0.1])
        with col_btn:
            run_mission = st.button("🔍 Search", type="primary", use_container_width=True)

        st.markdown("---")

        # System Status in Sidebar
        st.write("#### Connectivity")

        if config.is_lens_configured:
            st.markdown('<div class="status-badge status-ok">Lens.org API Active</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-err">Lens.org API Offline</div>', unsafe_allow_html=True)
            st.caption("Missing `LENS_ORG_API_TOKEN`")

        st.write("")  # Spacer

        if config.is_llm_configured:
            st.markdown('<div class="status-badge status-ok">LLM service connected</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-warn">LLM service offline</div>', unsafe_allow_html=True)

    return config, selected_language_code, start_date, end_date, run_mission
