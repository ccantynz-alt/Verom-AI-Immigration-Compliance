"""Tests for Tier 2 Differentiation features."""

from fastapi.testclient import TestClient

from immigration_compliance.api.app import app
from immigration_compliance.services.differentiation_service import (
    CompensationPlannerService,
    RegulatoryImpactEngine,
    SocialMediaAuditService,
    StrategyOptimizerService,
    TransparencyDashboardService,
)

client = TestClient(app)


# ── Strategy Optimizer ──

class TestStrategyOptimizer:
    def setup_method(self):
        self.svc = StrategyOptimizerService()

    def test_optimize_basic(self):
        results = self.svc.optimize({"education": "masters", "work_experience_years": 5})
        assert len(results) > 0
        assert all("fit_score" in r for r in results)
        assert results[0]["fit_score"] >= results[-1]["fit_score"]

    def test_includes_multiple_countries(self):
        results = self.svc.optimize({"education": "bachelors"})
        countries = {r["country"] for r in results}
        assert len(countries) >= 4

    def test_compare_countries(self):
        result = self.svc.compare_countries({"education": "masters"}, ["US", "UK"])
        assert all(r["country"] in ("US", "UK") for r in result["comparison"])

    def test_get_requirements(self):
        result = self.svc.get_country_requirements("US", "H-1B")
        assert result is not None
        assert result["visa_type"] == "H-1B"

    def test_unknown_pathway(self):
        result = self.svc.get_country_requirements("ZZ", "X-99")
        assert result is None

    def test_api_optimize(self):
        resp = client.post("/api/strategy/optimize", json={"education": "masters"})
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_api_requirements(self):
        resp = client.get("/api/strategy/requirements/US/H-1B")
        assert resp.status_code == 200


# ── Social Media Audit ──

class TestSocialMediaAudit:
    def setup_method(self):
        self.svc = SocialMediaAuditService()

    def test_audit_clean(self):
        result = self.svc.audit_profile("app-1", [{"platform": "LinkedIn", "handle": "@user"}])
        assert result["overall_risk"] == "low"

    def test_audit_flagged(self):
        result = self.svc.audit_profile("app-1", [
            {"platform": "Twitter/X", "handle": "@user", "has_immigration_criticism": True},
        ])
        assert result["overall_risk"] == "high"

    def test_disclosure_list(self):
        result = self.svc.generate_disclosure_list("app-1", [{"platform": "Facebook", "handle": "@test"}])
        assert len(result["disclosure_entries"]) == 1

    def test_required_platforms(self):
        platforms = self.svc.get_required_platforms()
        assert "Facebook" in platforms
        assert "Twitter/X" in platforms
        assert len(platforms) >= 15

    def test_consistency_pass(self):
        result = self.svc.check_consistency(
            {"platforms": [{"platform": "Facebook"}]},
            [{"platform": "Facebook"}],
        )
        assert result["consistent"]

    def test_consistency_fail(self):
        result = self.svc.check_consistency(
            {"platforms": []},
            [{"platform": "Instagram"}],
        )
        assert not result["consistent"]
        assert result["risk_level"] == "high"

    def test_api_platforms(self):
        resp = client.get("/api/social-audit/platforms")
        assert resp.status_code == 200


# ── Regulatory Impact Engine ──

class TestRegulatoryImpact:
    def setup_method(self):
        self.svc = RegulatoryImpactEngine()

    def test_analyze_regulation(self):
        result = self.svc.analyze_regulation({
            "title": "Test Rule",
            "affected_visa_types": ["H-1B"],
            "effective_date": "2026-04-01",
        })
        assert result["id"]
        assert result["urgency_level"] in ("critical", "high", "medium")

    def test_find_affected_cases(self):
        reg = self.svc.analyze_regulation({"title": "Rule", "affected_visa_types": ["H-1B"]})
        cases = [
            {"id": "c1", "visa_type": "H-1B"},
            {"id": "c2", "visa_type": "L-1"},
        ]
        affected = self.svc.find_affected_cases(reg["id"], cases)
        assert len(affected) == 1
        assert affected[0]["case_id"] == "c1"

    def test_action_plan(self):
        reg = self.svc.analyze_regulation({"title": "Rule", "affected_visa_types": ["H-1B"]})
        plan = self.svc.generate_action_plan(reg["id"], "case-1")
        assert len(plan["actions"]) >= 3

    def test_pending_regulations(self):
        pending = self.svc.get_pending_regulations()
        assert len(pending) >= 3

    def test_api_pending(self):
        resp = client.get("/api/regulatory-impact/pending")
        assert resp.status_code == 200


# ── Compensation Planner ──

class TestCompensationPlanner:
    def setup_method(self):
        self.svc = CompensationPlannerService()

    def test_analyze_low_wage(self):
        result = self.svc.analyze_impact({"salary": 95000, "soc_code": "15-1252", "msa": "National Average"})
        assert result["current_wage_level"] == 1
        assert result["selection_probability_at_current"] < 0.10

    def test_analyze_high_wage(self):
        result = self.svc.analyze_impact({"salary": 200000, "soc_code": "15-1252", "msa": "National Average"})
        assert result["current_wage_level"] == 4
        assert result["selection_probability_at_current"] > 0.30

    def test_optimize_workforce(self):
        employees = [
            {"salary": 95000, "soc_code": "15-1252", "msa": "National Average"},
            {"salary": 170000, "soc_code": "15-1252", "msa": "National Average"},
        ]
        result = self.svc.optimize_workforce(employees)
        assert result["total_employees"] == 2
        assert result["average_probability_after"] >= result["average_probability_before"]

    def test_prevailing_wages(self):
        result = self.svc.get_prevailing_wages("15-1252", "San Francisco-Oakland")
        assert result is not None
        assert result["wage_levels"][4] > result["wage_levels"][1]

    def test_roi(self):
        result = self.svc.calculate_roi(30000, 0.18)
        assert result["probability_gain"] == 0.18

    def test_api_analyze(self):
        resp = client.post("/api/compensation/analyze", json={"salary": 120000})
        assert resp.status_code == 200


# ── Transparency Dashboard ──

class TestTransparencyDashboard:
    def setup_method(self):
        self.svc = TransparencyDashboardService()

    def test_community_times(self):
        result = self.svc.get_community_times("I-129")
        assert result["data_points"] > 0
        assert result["min_days"] < result["max_days"]

    def test_submit_data(self):
        result = self.svc.submit_data_point("user-1", {
            "form_type": "I-129",
            "service_center": "California",
            "filed_date": "2025-10-01",
            "decision_date": "2026-02-15",
        })
        assert result["processing_days"] > 0

    def test_trends(self):
        trends = self.svc.get_trends("I-129")
        assert len(trends) >= 6

    def test_anomalies(self):
        anomalies = self.svc.get_anomalies()
        assert len(anomalies) >= 1

    def test_compare(self):
        result = self.svc.compare_official_vs_community("I-129")
        assert "official_avg_days" in result
        assert "community_avg_days" in result

    def test_api_times(self):
        resp = client.get("/api/transparency/times/I-129")
        assert resp.status_code == 200

    def test_api_trends(self):
        resp = client.get("/api/transparency/trends/I-129")
        assert resp.status_code == 200
