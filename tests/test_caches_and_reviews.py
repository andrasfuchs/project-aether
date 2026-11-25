from project_aether.core.reviews import (
    build_calibration_prompt_block,
    delete_review,
    export_reviews_json,
    get_review,
    import_reviews_json,
    list_reviews,
    save_review,
)
from project_aether.core.scoring_cache import (
    get_cached_score,
    load_scoring_cache,
    set_cached_score,
)
from project_aether.core.search_cache import (
    get_cached_search_results,
    load_search_cache,
    set_cached_search_results,
)
from project_aether.core.translation_service import (
    get_cached_translation,
    load_translation_cache,
    set_cached_translation,
)


def test_scoring_cache_invalidates_on_model_thinking_and_prompt(tmp_path):
    cache_file = tmp_path / "scoring_cache.jsonl"
    cache = load_scoring_cache(cache_file)

    set_cached_score(
        cache,
        record_id="REC-1",
        title="Plasma reactor",
        abstract="Hydrogen discharge",
        system_message="prompt v1",
        model="gemini-4-hydrogen",
        thinking_level="low",
        score=82.0,
        tags=["plasma"],
        features=["discharge"],
        rationale="Good match",
        append_path=cache_file,
        persist=True,
    )

    # Exact match hits
    hit = get_cached_score(
        cache, "REC-1", "Plasma reactor", "Hydrogen discharge", "prompt v1", "gemini-4-hydrogen", "low"
    )
    assert hit is not None
    assert hit["score"] == 82.0

    # Changing thinking_level, model, or prompt misses
    assert (
        get_cached_score(
            cache, "REC-1", "Plasma reactor", "Hydrogen discharge", "prompt v1", "gemini-4-hydrogen", "medium"
        )
        is None
    )
    assert (
        get_cached_score(
            cache, "REC-1", "Plasma reactor", "Hydrogen discharge", "prompt v2", "gemini-4-hydrogen", "low"
        )
        is None
    )

    # Reloading from JSONL preserves entry
    reloaded = load_scoring_cache(cache_file)
    hit2 = get_cached_score(
        reloaded, "REC-1", "Plasma reactor", "Hydrogen discharge", "prompt v1", "gemini-4-hydrogen", "low"
    )
    assert hit2 is not None and hit2["rationale"] == "Good match"


def test_search_cache_unbounded_ignores_end_date(tmp_path):
    cache_dir = tmp_path / "search_cache"
    cache = load_search_cache(cache_dir)

    set_cached_search_results(
        cache=cache,
        provider="lens",
        jurisdiction=None,
        start_date=None,
        end_date="2026-11-24",
        positive_keywords=[["spark"]],
        negative_keywords=["plug"],
        patent_status_filter=None,
        language="EN",
        limit=100,
        results={"data": [{"record_id": "R1"}]},
    )

    # Next day still hits when start_date is None
    hit = get_cached_search_results(
        cache=cache,
        provider="lens",
        jurisdiction=None,
        start_date=None,
        end_date="2026-11-25",
        positive_keywords=[["spark"]],
        negative_keywords=["plug"],
        patent_status_filter=None,
        language="EN",
        limit=100,
    )
    assert hit is not None
    assert hit["data"][0]["record_id"] == "R1"


def test_translation_cache_jsonl_roundtrip(tmp_path):
    cache_file = tmp_path / "translation_cache.jsonl"
    cache = load_translation_cache(cache_file)
    set_cached_translation(
        cache,
        source_id="REC-1",
        source_language="Russian",
        target_language="Hungarian",
        translated_text="Plazma kisülés",
        model="gemini-4-hydrogen",
        append_path=cache_file,
        persist=True,
    )
    reloaded = load_translation_cache(cache_file)
    assert get_cached_translation(reloaded, "REC-1", "Russian", "Hungarian") == "Plazma kisülés"


def test_reviews_sqlite_crud_calibration_and_export(tmp_path):
    db_path = tmp_path / "aether.db"
    save_review(
        record_id="REC-HIGH",
        user_score=92,
        notes="Strong excess heat claim in Pd-D2",
        title="Anomalous heat cell",
        jurisdiction="RU",
        doc_number="RU123",
        llm_score=85.0,
        db_path=db_path,
    )
    save_review(
        record_id="REC-LOW",
        user_score=5,
        notes="Wire bonding EDM noise",
        title="Wire bonding spark apparatus",
        jurisdiction="US",
        doc_number="US456",
        llm_score=45.0,
        db_path=db_path,
    )

    assert get_review("REC-HIGH", db_path=db_path)["user_score"] == 92.0
    assert len(list_reviews(min_score=60, db_path=db_path)) == 1
    assert len(list_reviews(max_score=30, db_path=db_path)) == 1

    cal_block = build_calibration_prompt_block(db_path=db_path)
    assert "Score 92/100" in cal_block
    assert "Score 5/100" in cal_block
    assert "Wire bonding EDM noise" in cal_block

    exported = export_reviews_json(db_path=db_path)
    assert delete_review("REC-LOW", db_path=db_path) is True
    assert len(list_reviews(db_path=db_path)) == 1

    imported = import_reviews_json(exported, db_path=db_path)
    assert imported == 2
    assert len(list_reviews(db_path=db_path)) == 2


def test_patent_pdf_storage_and_brief(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import patch

    from project_aether.core.llm_advisor import (
        delete_patent_pdf,
        generate_technical_brief,
        load_patent_pdf,
        save_patent_pdf,
    )

    pdf_dir = tmp_path / "patent_pdfs"
    sample_bytes = b"%PDF-1.4 fake patent pdf content"
    saved_path = save_patent_pdf("071-049-022", sample_bytes, pdf_dir=pdf_dir)
    assert saved_path.exists()
    assert load_patent_pdf("071-049-022", pdf_dir=pdf_dir) == sample_bytes

    mock_resp = SimpleNamespace(text="## Apparatus\nNickel cathode in H2.")
    with patch("project_aether.core.llm_advisor.generate_content", return_value=mock_resp) as mock_call:
        brief = generate_technical_brief(
            title="Test",
            abstract="Short",
            claims="",
            jurisdiction="RU",
            status_summary="Refused",
            classifications=["H05H 1/00"],
            output_language="Hungarian",
            api_key="fake",
            pdf_bytes=sample_bytes,
        )
    assert "Uploaded Full Patent PDF" in brief
    assert "Nickel cathode" in brief
    assert isinstance(mock_call.call_args.kwargs["contents"], list)

    assert delete_patent_pdf("071-049-022", pdf_dir=pdf_dir) is True
    assert load_patent_pdf("071-049-022", pdf_dir=pdf_dir) is None
