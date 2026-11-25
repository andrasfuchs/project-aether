from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from project_aether.agents.analyst import AnalystAgent
from project_aether.services.search import execute_patent_search
from project_aether.tools.inpadoc import StatusAnalysis, StatusSeverity


def _status(severity: StatusSeverity) -> StatusAnalysis:
    return StatusAnalysis(
        is_refused=(severity == StatusSeverity.HIGH),
        is_withdrawn=False,
        is_lapsed=False,
        is_expired=False,
        is_inactive=False,
        is_active=(severity == StatusSeverity.LOW),
        is_pending=False,
        severity=severity,
        refusal_reason="Test",
        code_found=None,
        jurisdiction="RU",
        interpretation="Test",
    )


def test_triage_rules_score_driven():
    analyst = AnalystAgent(
        keyword_config={"English": {"positive": [["hydrogen"]], "negative": []}},
        relevance_threshold=40.0,
        high_threshold=70.0,
    )
    # High score active patent -> HIGH
    assert analyst._determine_intelligence_value(_status(StatusSeverity.LOW), 85.0, []) == "HIGH"
    # Low score refused automotive patent -> LOW (not promoted to MEDIUM)
    assert analyst._determine_intelligence_value(_status(StatusSeverity.HIGH), 10.0, []) == "LOW"
    # Medium score + substantive refusal -> HIGH
    assert analyst._determine_intelligence_value(_status(StatusSeverity.HIGH), 55.0, []) == "HIGH"
    # Medium score active -> MEDIUM
    assert analyst._determine_intelligence_value(_status(StatusSeverity.LOW), 55.0, []) == "MEDIUM"


def test_analyst_native_scoring_with_mocked_llm(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    from project_aether.core.config import reload_config
    reload_config()

    analyst = AnalystAgent(
        keyword_config={"English": {"positive": [["plasma", "spark"]], "negative": ["spark plug"]}},
    )
    analyst.scoring_cache = {"version": 3, "entries": {}}

    mock_resp = SimpleNamespace(
        text='{"score": 88, "title_en": "Hydrogen plasma discharge reactor", '
             '"domain_category": "Anomalous Plasma/LENR", "tags": ["plasma", "hydrogen"], '
             '"features": ["pulsed cathode"], "rationale": "Describes excess heat in H2 discharge."}'
    )

    patent = {
        "record_id": "REC-RU-1",
        "lens_id": "REC-RU-1",
        "provider_name": "lens",
        "provider_record_url": "https://www.lens.org/lens/patent/REC-RU-1/frontpage",
        "jurisdiction": "RU",
        "doc_number": "RU999",
        "date_published": "2025-01-10",
        "biblio": {
            "invention_title": [{"text": "Плазменный реактор", "lang": "ru"}],
            "parties": {
                "inventors": [{"extracted_name": {"value": "Ivanov I."}}],
                "applicants": [{"extracted_name": {"value": "Lab X"}}],
            },
            "classifications_ipcr": [{"symbol": "H05H 1/00"}],
        },
        "abstract": [{"text": "Описание разряда в водороде", "lang": "ru"}],
        "legal_status": {"patent_status": "REJECTED", "events": [{"event_code": "FC9A"}]},
    }

    with patch("project_aether.agents.analyst.generate_content", return_value=mock_resp), \
         patch("project_aether.agents.analyst.set_cached_score"):
        assessment = analyst.analyze_patent(patent)

    assert assessment.relevance_score == 88.0
    assert assessment.title_en == "Hydrogen plasma discharge reactor"
    assert assessment.domain_category == "Anomalous Plasma/LENR"
    assert assessment.rationale == "Describes excess heat in H2 discharge."
    assert assessment.intelligence_value == "HIGH"
    assert assessment.applicants == ["Lab X"]
    assert "H05H 1/00" in assessment.all_classifications


def test_search_deduplicates_across_languages(tmp_path, monkeypatch):
    monkeypatch.setenv("PATENT_PROVIDER", "lens")
    monkeypatch.setenv("LENS_ORG_API_TOKEN", "fake-lens")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from project_aether.core.config import reload_config
    reload_config()

    shared_patent = {
        "record_id": "DUP-1",
        "lens_id": "DUP-1",
        "jurisdiction": "EP",
        "doc_number": "EP123",
        "biblio": {"invention_title": [{"text": "Hydrogen spark", "lang": "en"}]},
        "abstract": [{"text": "Plasma discharge", "lang": "en"}],
        "legal_status": {"patent_status": "ACTIVE", "events": []},
    }

    mock_search = AsyncMock(
        return_value={"data": [dict(shared_patent)], "total_available": 1, "filtered_total": 1}
    )

    with patch("project_aether.services.search.LensConnector.search_by_jurisdiction", new=mock_search), \
         patch("project_aether.services.search.get_cached_search_results", return_value=None), \
         patch("project_aether.services.search.set_cached_search_results"), \
         patch("project_aether.services.search.save_keyword_cache"), \
         patch("project_aether.services.search.build_calibration_prompt_block", return_value=""):
        res = execute_patent_search(
            language_codes=["EN", "DE"],
            language_names=["English", "German"],
            keyword_config={"English": {"positive": [["hydrogen"]], "negative": []}},
            keyword_cache={"version": 1, "keyword_sets": {}, "history": [], "translations": {}},
        )

    assert len(res.raw_results) == 1
    assert len(res.assessments) == 1
    assert res.search_diagnostics[1]["duplicates_skipped"] == 1
