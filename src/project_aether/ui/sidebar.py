from datetime import datetime
import asyncio

import streamlit as st

from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.keyword_translation import (
    load_keyword_cache,
    save_keyword_cache,
    ensure_keyword_set,
    get_history_entries,
    delete_keyword_set,
)
from project_aether.core.keywords import DEFAULT_KEYWORDS
from project_aether.tools.epo_api import EPOConnector
from project_aether.tools.lens_api import LensConnector


def load_keyword_set_callback(entry):
    """Callback to load keyword set into session state before widget rendering."""
    if "keyword_config" in st.session_state:
        st.session_state["keyword_config"].setdefault("English", {})["positive"] = entry.get("include", [])
        st.session_state["keyword_config"].setdefault("English", {})["negative"] = entry.get("exclude", [])
    
    # Load the keyword set name
    st.session_state["keyword_set_name"] = entry.get("label", "")

    # Increment widget version to force recreation
    st.session_state["keyword_widget_version"] = st.session_state.get("keyword_widget_version", 0) + 1


def on_keyword_name_change():
    """Callback when the keyword set name textbox changes."""
    name = st.session_state.get("sidebar_set_label", "").strip()
    cache = st.session_state.get("keyword_cache", {})
    
    # Check if a keyword set with this name exists in the cache
    keyword_sets = cache.get("keyword_sets", {})
    name_exists = any(
        entry.get("label") == name 
        for entry in keyword_sets.values()
    )
    
    # Store mode and the associated set_id if updating
    if name and name_exists:
        # Find the set_id for this named entry
        for set_id, entry in keyword_sets.items():
            if entry.get("label") == name:
                st.session_state["keyword_set_mode"] = "UPDATE"
                st.session_state["keyword_set_update_id"] = set_id
                st.session_state["keyword_set_original_include"] = entry.get("include", [])
                st.session_state["keyword_set_original_exclude"] = entry.get("exclude", [])
                break
    else:
        st.session_state["keyword_set_mode"] = "SAVE"
        st.session_state["keyword_set_update_id"] = None


def render_sidebar(language_map):
    with st.sidebar:
        config = get_config()

        # Use infinite date window (no date filtering)
        end_date = datetime.now()
        start_date = None

        # Initialize language selection in session state
        if "selected_languages" not in st.session_state:
            st.session_state.selected_languages = ["English"]

        language_options = list(language_map.keys())
        selected_language_names = st.multiselect(
            "Languages",
            options=language_options,
            default=st.session_state.selected_languages,
            help="Select one or more languages for the search query. Searches will be performed sequentially and results accumulated.",
        )

        # Store selected languages
        if selected_language_names:
            st.session_state.selected_languages = selected_language_names
        else:
            st.warning("Please select at least one language.")
            selected_language_names = ["English"]
            st.session_state.selected_languages = selected_language_names
        
        selected_language_codes = [language_map[lang] for lang in selected_language_names]

        # Jurisdiction is set to ALL by default (no filter)
        selected_jurisdictions = None

        keyword_config = st.session_state.get("keyword_config", DEFAULT_KEYWORDS)
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        cache = st.session_state.get("keyword_cache", {})
        widget_version = st.session_state.get("keyword_widget_version", 0)

        with st.expander("Keyword set", expanded=True):
            set_label = st.text_input("Name (optional)", key="sidebar_set_label", value=st.session_state.get("keyword_set_name", ""), placeholder="e.g. My Custom Keywords", on_change=on_keyword_name_change)

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

            # Determine button mode (SAVE vs UPDATE)
            mode = st.session_state.get("keyword_set_mode", "SAVE")
            button_label = "💾 Update" if mode == "UPDATE" else "💾 Save"

            if st.button(button_label, use_container_width=True):
                if mode == "UPDATE":
                    # In UPDATE mode, check if terms have changed
                    original_include = st.session_state.get("keyword_set_original_include", [])
                    original_exclude = st.session_state.get("keyword_set_original_exclude", [])
                    
                    if updated_include != original_include or updated_exclude != original_exclude:
                        # Terms changed - delete old entry and its translations
                        update_id = st.session_state.get("keyword_set_update_id")
                        if update_id:
                            delete_keyword_set(cache, update_id)
                        
                        # Save as new keyword set with the same label
                        ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                        save_keyword_cache(cache)
                        st.session_state["keyword_cache"] = cache
                        st.success("Keyword set updated")
                    else:
                        st.info("No changes to save")
                else:
                    # In SAVE mode, just save as new
                    ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                    save_keyword_cache(cache)
                    st.session_state["keyword_cache"] = cache
                    st.success("Keyword set saved")

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

        provider_name = "EPO"
        if config.is_epo_configured:
            st.markdown(
                f'<div class="status-badge status-ok">Primary Patent Provider ({provider_name}) Active</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-badge status-err">Primary Patent Provider ({provider_name}) Offline</div>',
                unsafe_allow_html=True,
            )
            st.caption("Missing `EPO_CONSUMER_KEY` and/or `EPO_CONSUMER_SECRET`")

        fallback_name = "LENS"
        if config.is_lens_configured:
            st.markdown(
                f'<div class="status-badge status-ok">{fallback_name} fallback available</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-badge status-warn">{fallback_name} fallback unavailable</div>',
                unsafe_allow_html=True,
            )

        st.write("")  # Spacer

        if config.is_llm_configured:
            st.markdown('<div class="status-badge status-ok">LLM service connected</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-warn">LLM service offline</div>', unsafe_allow_html=True)

    return config, selected_language_codes, selected_language_names, start_date, end_date, run_mission
