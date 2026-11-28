from datetime import datetime, timedelta

import streamlit as st

from project_aether.core.config import get_config
from project_aether.core.keyword_helpers import get_active_english_keywords
from project_aether.core.keyword_translation import (
    delete_keyword_set,
    ensure_keyword_set,
    get_cached_translation,
    get_history_entries,
    keyword_set_id,
    save_keyword_cache,
    set_cached_translation,
)


def load_keyword_set_callback(entry):
    """Callback to load keyword set into session state before widget rendering."""
    if "keyword_config" in st.session_state:
        st.session_state["keyword_config"].setdefault("English", {})["positive"] = entry.get("include", [])
        st.session_state["keyword_config"].setdefault("English", {})["negative"] = entry.get("exclude", [])

    st.session_state["keyword_set_name"] = entry.get("label", "")
    st.session_state["keyword_widget_version"] = st.session_state.get("keyword_widget_version", 0) + 1


def on_keyword_name_change():
    """Callback when the keyword set name textbox changes."""
    name = st.session_state.get("sidebar_set_label", "").strip()
    cache = st.session_state.get("keyword_cache", {})
    keyword_sets = cache.get("keyword_sets", {})

    for set_id, entry in keyword_sets.items():
        if name and entry.get("label") == name:
            st.session_state["keyword_set_mode"] = "UPDATE"
            st.session_state["keyword_set_update_id"] = set_id
            st.session_state["keyword_set_original_include"] = entry.get("include", [])
            st.session_state["keyword_set_original_exclude"] = entry.get("exclude", [])
            return

    st.session_state["keyword_set_mode"] = "SAVE"
    st.session_state["keyword_set_update_id"] = None


def render_sidebar(language_map, jurisdiction_map=None):
    with st.sidebar:
        config = get_config()

        st.markdown('<div class="aether-sidebar-title">Query builder</div>', unsafe_allow_html=True)

        if "selected_languages" not in st.session_state:
            st.session_state.selected_languages = ["English"]

        language_options = list(language_map.keys())
        selected_language_names = st.multiselect(
            "Query languages",
            options=language_options,
            default=st.session_state.selected_languages,
            help="Select one or more languages. Searches run sequentially and results are deduplicated.",
        )

        if selected_language_names:
            st.session_state.selected_languages = selected_language_names
        else:
            st.warning("Select at least one language.")
            selected_language_names = ["English"]
            st.session_state.selected_languages = selected_language_names

        selected_language_codes = [language_map[lang] for lang in selected_language_names]

        keyword_config = st.session_state.get(
            "keyword_config",
            {"English": {"positive": [], "negative": []}},
        )
        include_terms, exclude_terms = get_active_english_keywords(keyword_config)
        cache = st.session_state.get("keyword_cache", {})
        widget_version = st.session_state.get("keyword_widget_version", 0)

        with st.expander("Keyword set", expanded=True):
            set_label = st.text_input(
                "Set name",
                key="sidebar_set_label",
                value=st.session_state.get("keyword_set_name", ""),
                placeholder="e.g. Lattice hydrogen anomalies",
                on_change=on_keyword_name_change,
            )

            include_value = (
                "\n".join(", ".join(group) for group in include_terms)
                if include_terms and isinstance(include_terms[0], list)
                else "\n".join(str(term) for term in include_terms)
            )
            include_text = st.text_area(
                "Include terms (comma-separated synonyms per line)",
                value=include_value,
                height=115,
                key=f"sidebar_include_terms_{widget_version}",
            )
            exclude_text = st.text_area(
                "Exclude terms",
                value=", ".join(exclude_terms),
                height=95,
                key=f"sidebar_exclude_terms_{widget_version}",
            )

            updated_include = [
                [t.strip() for t in line.split(",") if t.strip()]
                for line in include_text.split("\n")
                if line.strip()
            ]
            updated_exclude = [term.strip() for term in exclude_text.split(",") if term.strip()]
            keyword_config.setdefault("English", {})["positive"] = updated_include
            keyword_config.setdefault("English", {})["negative"] = updated_exclude
            st.session_state["keyword_config"] = keyword_config

            st.caption(
                f"{sum(len(g) for g in updated_include)} include terms in {len(updated_include)} groups · "
                f"{len(updated_exclude)} exclude terms"
            )

            mode = st.session_state.get("keyword_set_mode", "SAVE")
            button_label = "Update set" if mode == "UPDATE" else "Save set"

            if st.button(button_label, width="stretch"):
                if mode == "UPDATE":
                    original_include = st.session_state.get("keyword_set_original_include", [])
                    original_exclude = st.session_state.get("keyword_set_original_exclude", [])
                    if updated_include != original_include or updated_exclude != original_exclude:
                        update_id = st.session_state.get("keyword_set_update_id")
                        if update_id:
                            delete_keyword_set(cache, update_id)
                        ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                        save_keyword_cache(cache)
                        st.session_state["keyword_cache"] = cache
                        st.success("Keyword set updated.")
                    else:
                        st.info("No changes to save.")
                else:
                    ensure_keyword_set(cache, updated_include, updated_exclude, label=set_label)
                    save_keyword_cache(cache)
                    st.session_state["keyword_cache"] = cache
                    st.success("Keyword set saved.")

            # Inspect and edit cached translations for selected non-English languages
            non_en_langs = [lang for lang in selected_language_names if lang != "English"]
            if non_en_langs and updated_include:
                active_set_id = keyword_set_id(updated_include, updated_exclude)
                edit_lang = st.selectbox(
                    "Edit cached translation",
                    options=non_en_langs,
                    key="sidebar_edit_trans_lang",
                )
                cached_trans = get_cached_translation(cache, active_set_id, edit_lang)
                if cached_trans:
                    t_inc = "\n".join(", ".join(g) for g in cached_trans.get("include", []))
                    t_exc = ", ".join(cached_trans.get("exclude", []))
                    new_t_inc = st.text_area(
                        f"{edit_lang} include",
                        value=t_inc,
                        height=75,
                        key=f"trans_inc_{active_set_id}_{edit_lang}",
                    )
                    new_t_exc = st.text_input(
                        f"{edit_lang} exclude",
                        value=t_exc,
                        key=f"trans_exc_{active_set_id}_{edit_lang}",
                    )
                    if st.button("Save translation", key=f"save_trans_{active_set_id}_{edit_lang}", width="stretch"):
                        parsed_inc = [
                            [t.strip() for t in ln.split(",") if t.strip()]
                            for ln in new_t_inc.split("\n")
                            if ln.strip()
                        ]
                        parsed_exc = [t.strip() for t in new_t_exc.split(",") if t.strip()]
                        set_cached_translation(
                            cache,
                            set_id=active_set_id,
                            language=edit_lang,
                            include_terms=parsed_inc,
                            exclude_terms=parsed_exc,
                            source="manual",
                        )
                        save_keyword_cache(cache)
                        st.session_state["keyword_cache"] = cache
                        st.success(f"Saved {edit_lang} translation.")
                else:
                    st.caption(f"No cached {edit_lang} translation yet. Auto-translates on search.")

        with st.expander("Saved keyword sets", expanded=False):
            history_entries = get_history_entries(cache)
            if not history_entries:
                st.caption("No saved keyword sets yet.")
            else:
                labels = [entry.get("label", entry["id"]) for entry in history_entries]
                selected_label = st.selectbox("Saved set", options=labels)
                selected_entry = next(
                    (entry for entry in history_entries if entry.get("label", entry["id"]) == selected_label),
                    history_entries[0],
                )
                col_load, col_delete = st.columns(2)
                with col_load:
                    if st.button("Load", width="stretch", on_click=load_keyword_set_callback, args=(selected_entry,)):
                        st.success("Keyword set loaded.")
                        st.rerun()
                with col_delete:
                    if st.button("Delete", width="stretch"):
                        delete_keyword_set(cache, selected_entry["id"])
                        save_keyword_cache(cache)
                        st.session_state["keyword_cache"] = cache
                        st.success("Keyword set deleted.")
                        st.rerun()

        # --- OPTIONAL SEARCH FILTERS ---
        selected_jurisdiction: str | None = None
        selected_statuses: list[str] | None = None
        start_date: datetime | None = None
        end_date: datetime = datetime.now()
        force_refresh = False

        with st.expander("Search filters", expanded=False):
            if jurisdiction_map:
                jur_names = list(jurisdiction_map.keys())
                chosen_jur = st.selectbox("Jurisdiction", jur_names, index=0, key="sidebar_jurisdiction")
                code = jurisdiction_map[chosen_jur]
                selected_jurisdiction = None if code == "ALL" else code

            status_opts = ["REJECTED", "DISCONTINUED", "WITHDRAWN", "ACTIVE", "PENDING", "EXPIRED"]
            chosen_statuses = st.multiselect(
                "Legal status (Lens)",
                options=status_opts,
                default=[],
                placeholder="All statuses",
                key="sidebar_statuses",
            )
            selected_statuses = chosen_statuses or None

            window_opt = st.selectbox(
                "Publication window",
                ["All time", "Last 7 days", "Last 30 days", "Last 90 days", "Last 365 days"],
                index=0,
                key="sidebar_date_window",
            )
            days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90, "Last 365 days": 365}
            if window_opt in days_map:
                start_date = end_date - timedelta(days=days_map[window_opt])

            force_refresh = st.checkbox(
                "Bypass search cache",
                value=False,
                key="sidebar_force_refresh",
            )

        run_mission = st.button("Run search", type="primary", width="stretch")

        st.markdown("---")

        # --- CONNECTIVITY ---
        primary_provider = config.normalized_patent_provider
        secondary_provider = "lens" if primary_provider == "epo" else "epo"

        provider_labels = {"epo": "EPO OPS", "lens": "Lens.org"}
        provider_available = {"epo": config.is_epo_configured, "lens": config.is_lens_configured}

        p_dot = "aether-dot--ok" if provider_available[primary_provider] else "aether-dot--err"
        p_state = "Ready" if provider_available[primary_provider] else "Missing"
        s_dot = "aether-dot--ok" if provider_available[secondary_provider] else "aether-dot--warn"
        s_state = "Ready" if provider_available[secondary_provider] else "Offline"
        g_dot = "aether-dot--ok" if config.is_llm_configured else "aether-dot--warn"
        g_state = "Ready" if config.is_llm_configured else "Offline"

        st.markdown(
            f"""
            <div class="aether-conn-list">
                <div class="aether-conn-row">
                    <span>Primary · {provider_labels[primary_provider]}</span>
                    <span class="aether-status-item"><span class="aether-dot {p_dot}"></span>{p_state}</span>
                </div>
                <div class="aether-conn-row">
                    <span>Fallback · {provider_labels[secondary_provider]}</span>
                    <span class="aether-status-item"><span class="aether-dot {s_dot}"></span>{s_state}</span>
                </div>
                <div class="aether-conn-row">
                    <span>Scoring · Gemini</span>
                    <span class="aether-status-item"><span class="aether-dot {g_dot}"></span>{g_state}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Sources: [EPO OPS](https://developers.epo.org/) · [Lens.org](https://www.lens.org/)")

    return (
        config,
        selected_language_codes,
        selected_language_names,
        start_date,
        end_date,
        selected_jurisdiction,
        selected_statuses,
        force_refresh,
        run_mission,
    )
