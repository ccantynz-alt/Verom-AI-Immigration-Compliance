"""Tests for the SOC Code Selection Engine."""

from immigration_compliance.services.soc_code_service import (
    SocCodeService,
    SOC_CATALOG,
    SOC_BY_CODE,
)


def test_catalog_size():
    assert len(SOC_CATALOG) >= 30


def test_software_developer_recommends_15_1252():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Senior Software Engineer",
        duties="Design and develop software, build applications, code, debug",
        skills=["Python", "AWS", "Kubernetes"],
    )
    assert r["recommendations"][0]["soc_code"] == "15-1252"


def test_data_scientist_recommends_15_2051():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Senior Data Scientist",
        duties="Build machine learning models, statistical analysis, predictive modeling",
        skills=["Python", "TensorFlow", "Statistics"],
    )
    assert r["recommendations"][0]["soc_code"] == "15-2051"


def test_engineering_manager_with_pref_recommends_11_3021():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="VP of Engineering",
        duties="Manage engineering team, supervise team, technical leadership",
        skills=["Leadership"],
        prefer_managerial=True,
    )
    assert r["recommendations"][0]["soc_code"] == "11-3021"


def test_pharmacist_flagged_schedule_a():
    svc = SocCodeService()
    r = svc.recommend(job_title="Pharmacist", duties="Dispense medication", skills=["PharmD"])
    top = r["recommendations"][0]
    assert top["soc_code"] == "29-1051"
    assert top["perm_schedule_a"] is True


def test_research_preference_boosts_o1_eligible():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Research Scientist",
        duties="Conduct research, publish papers, develop algorithms, novel methods",
        skills=["PhD", "Machine Learning"],
        prefer_research=True,
    )
    top_codes = [rec["soc_code"] for rec in r["recommendations"][:3]]
    assert "15-1221" in top_codes


def test_unknown_title_falls_back_with_low_score():
    svc = SocCodeService()
    r = svc.recommend(job_title="Bartender Mixologist", duties="", skills=[])
    if r["recommendations"]:
        # Low confidence
        assert r["recommendations"][0]["score"] <= 25


def test_catalog_search():
    results = SocCodeService.list_catalog(search="developer")
    assert any("Software Developer" in e["title"] for e in results)


def test_catalog_search_case_insensitive():
    results = SocCodeService.list_catalog(search="NURSE")
    assert any("Nurse" in e["title"] for e in results)


def test_get_by_code_returns_entry():
    e = SocCodeService.get_by_code("15-1252")
    assert e is not None
    assert e["title"] == "Software Developers"


def test_get_by_code_unknown_returns_none():
    assert SocCodeService.get_by_code("99-9999") is None


def test_recommendation_persisted():
    svc = SocCodeService()
    r = svc.recommend(job_title="Software Engineer")
    assert svc.get_recommendation(r["id"])["id"] == r["id"]


def test_managerial_preference_does_not_promote_non_managerial():
    """Even with prefer_managerial=True, a software engineer role
    shouldn't be classified as a managerial occupation."""
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Junior Software Engineer",
        duties="Write code, fix bugs",
        skills=["Python"],
        prefer_managerial=True,
    )
    top = r["recommendations"][0]
    # Top should still be 15-1252 (developer), not a manager code
    assert top["soc_code"] == "15-1252"


def test_components_breakdown_returned():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Software Engineer",
        duties="develop software",
        skills=["python"],
    )
    top = r["recommendations"][0]
    components = top["components"]
    assert "title" in components
    assert "duties" in components
    assert "skills" in components


def test_soc_by_code_indexed():
    assert "15-1252" in SOC_BY_CODE
    assert SOC_BY_CODE["15-1252"]["title"] == "Software Developers"


def test_lawyer_recommends_23_1011():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Senior Attorney",
        duties="Provide legal advice, draft contracts",
        skills=["JD", "Bar Admission"],
    )
    assert r["recommendations"][0]["soc_code"] == "23-1011"


def test_market_research_recommends_13_1161():
    svc = SocCodeService()
    r = svc.recommend(
        job_title="Senior Market Researcher",
        duties="Conduct market research, consumer analysis",
        skills=["SPSS"],
    )
    assert r["recommendations"][0]["soc_code"] == "13-1161"
