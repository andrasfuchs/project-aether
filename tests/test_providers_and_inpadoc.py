from xml.etree import ElementTree as ET

from project_aether.tools.epo_api import EPOConnector
from project_aether.tools.inpadoc import StatusSeverity, analyze_legal_status
from project_aether.tools.lens_api import LensConnector


def test_lens_grouped_synonym_query():
    connector = LensConnector(api_token="test-token")
    query = connector.build_keyword_search_query(
        jurisdictions=["RU"],
        start_date=None,
        positive_keywords=[["spark", "electric discharge"], ["hydrogen"]],
        negative_keywords=["spark plug"],
        language="HU",
    )
    assert query["language"] == "other"
    must = query["query"]["bool"]["must"]
    # 1 jurisdiction + 2 positive groups
    assert len(must) == 3
    assert len(query["query"]["bool"]["must_not"]) == 1


def test_epo_normalize_grouped_keywords():
    normalized = EPOConnector._normalize_keyword_list(
        [["spark", "electric discharge"], ["hydrogen", "spark"]]
    )
    assert normalized == ["spark", "electric discharge", "hydrogen"]


def test_epo_extract_legal_status_does_not_misclassify_granted():
    xml = """
    <ops:world-patent-data xmlns:ops="http://ops.epo.org">
      <ops:patent-family>
        <ops:family-member>
          <ops:legal>
            <ops:L008EP>GRNT</ops:L008EP>
            <ops:L019EP>20240501</ops:L019EP>
          </ops:legal>
          <ops:legal>
            <ops:L008EP>STAA</ops:L008EP>
            <ops:L019EP>20230101</ops:L019EP>
          </ops:legal>
        </ops:family-member>
      </ops:patent-family>
    </ops:world-patent-data>
    """
    connector = EPOConnector(consumer_key="k", consumer_secret="s")
    root = ET.fromstring(xml)
    status = connector._extract_legal_status(root)
    assert status["patent_status"] != "REFUSED"
    # Sorted ascending: oldest first, newest last
    assert status["events"][0]["event_code"] == "STAA"
    assert status["events"][-1]["event_code"] == "GRNT"


def test_inpadoc_sorts_events_chronologically():
    record = {
        "jurisdiction": "RU",
        "legal_status": {
            "patent_status": "ACTIVE",
            "events": [
                {"event_code": "GRNT", "date": "2024-06-01", "description": "Granted"},
                {"event_code": "STAA", "date": "2023-01-01", "description": "Published"},
            ],
        },
    }
    res = analyze_legal_status(record)
    assert res.code_found == "GRNT"
    assert res.is_active is True

    refused_record = {
        "jurisdiction": "RU",
        "legal_status": {
            "patent_status": "DISCONTINUED",
            "events": [
                {"event_code": "FC9A", "date": "2024-02-01", "description": "Refusal"},
            ],
        },
    }
    ref_res = analyze_legal_status(refused_record)
    assert ref_res.is_refused is True
    assert ref_res.severity == StatusSeverity.HIGH
