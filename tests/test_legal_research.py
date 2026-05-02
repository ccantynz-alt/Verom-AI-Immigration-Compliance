"""Tests for the AI Legal Research engine."""

from immigration_compliance.services.legal_research_service import (
    LegalResearchService,
    CORPUS,
    AUTHORITY_TYPES,
    PRECEDENTIAL_WEIGHT,
)


def test_corpus_size_reasonable():
    assert len(CORPUS) >= 20


def test_corpus_covers_major_topics():
    tags_lower = {t.lower() for entry in CORPUS for t in entry.get("tags", [])}
    assert "h-1b" in tags_lower
    assert "eb-1a" in tags_lower
    assert "i-485" in tags_lower
    assert "i-130" in tags_lower
    assert "asylum" in tags_lower


def test_authority_types_cover_all():
    types_in_corpus = {entry["type"] for entry in CORPUS}
    expected = {"statute", "regulation", "policy_manual", "bia_precedent", "circuit_court"}
    assert expected <= types_in_corpus


def test_search_specialty_occupation_returns_relevant_results():
    svc = LegalResearchService()
    r = svc.search("specialty occupation H-1B")
    assert r["total_results"] > 0
    titles = [hit["title"] for hit in r["results"]]
    assert any("Specialty Occupation" in t for t in titles)


def test_search_kazarian_returns_kazarian():
    svc = LegalResearchService()
    r = svc.search("Kazarian")
    citations = [hit["citation"] for hit in r["results"]]
    assert any("Kazarian" in c for c in citations)


def test_search_filter_by_authority_type():
    svc = LegalResearchService()
    r = svc.search("specialty", authority_types=["regulation"])
    for hit in r["results"]:
        assert hit["type"] == "regulation"


def test_search_filter_by_tags():
    svc = LegalResearchService()
    r = svc.search("", tags=["asylum"])
    for hit in r["results"]:
        assert any(t.lower() == "asylum" for t in hit.get("tags", []))


def test_search_requires_query_or_tags():
    svc = LegalResearchService()
    try:
        svc.search("")
        assert False
    except ValueError:
        pass


def test_search_filter_by_min_year():
    svc = LegalResearchService()
    r = svc.search("", tags=["EB-1A"], min_year=2010)
    for hit in r["results"]:
        assert hit.get("year", 0) >= 2010


def test_find_citations_for_section():
    svc = LegalResearchService()
    section = "The position duties demonstrate specialty occupation under the regulatory tests."
    cites = svc.find_citations_for_section(section)
    assert len(cites) > 0
    # Top hit should be specialty-occupation related
    assert any("specialty" in (c["title"] + " " + c["holding"]).lower() for c in cites)


def test_find_citations_for_issue():
    svc = LegalResearchService()
    cites = svc.find_citations_for_issue("specialty occupation")
    assert len(cites) > 0


def test_get_by_id():
    a = LegalResearchService.get_by_id("kazarian-uscis")
    assert a is not None
    assert "Kazarian" in a["citation"]


def test_get_by_id_missing_returns_none():
    assert LegalResearchService.get_by_id("does-not-exist") is None


def test_search_logs_recorded():
    svc = LegalResearchService()
    svc.search("specialty")
    svc.search("asylum")
    log = svc.get_recent_searches()
    assert len(log) == 2


def test_results_sorted_by_relevance():
    svc = LegalResearchService()
    r = svc.search("specialty occupation H-1B Wage Level I")
    scores = [hit["relevance_score"] for hit in r["results"]]
    assert scores == sorted(scores, reverse=True)


def test_precedential_weights_present():
    assert PRECEDENTIAL_WEIGHT["supreme_court"] >= PRECEDENTIAL_WEIGHT["circuit_court"]
    assert PRECEDENTIAL_WEIGHT["circuit_court"] >= PRECEDENTIAL_WEIGHT["aao_decision"]


def test_score_breakdown_returned_with_results():
    svc = LegalResearchService()
    r = svc.search("Kazarian")
    if r["results"]:
        assert "score_breakdown" in r["results"][0]


def test_authority_types_listing():
    types = LegalResearchService.list_authority_types()
    assert set(types) == set(AUTHORITY_TYPES)


def test_citations_for_dhanasar():
    svc = LegalResearchService()
    cites = svc.find_citations_for_issue("Dhanasar")
    citations = [c["citation"] for c in cites]
    assert any("Dhanasar" in c for c in citations)


def test_no_query_match_returns_empty_or_low_score():
    svc = LegalResearchService()
    r = svc.search("completely unrelated nonsense words zyzzyx")
    # Either no results or all very low score
    for hit in r["results"]:
        assert hit["relevance_score"] < 20


def test_tags_listing_complete():
    tags = LegalResearchService.list_tags()
    assert "specialty occupation" in tags or "Specialty Occupation" in [t.lower() for t in tags] or any("specialty" in t for t in tags)


def test_marriage_fraud_authorities_findable():
    svc = LegalResearchService()
    r = svc.search("marriage fraud 204(c)")
    citations = [hit["citation"] for hit in r["results"]]
    assert any("204(c)" in c or "Tawfik" in c for c in citations)
