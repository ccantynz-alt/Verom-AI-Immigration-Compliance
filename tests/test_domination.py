"""Tests for Tier 1 Market Domination features."""

import pytest
from fastapi.testclient import TestClient

from immigration_compliance.api.app import app
from immigration_compliance.services.domination_service import (
    AgenticPipelineService,
    EADGapRiskService,
    H1BLotterySimulatorService,
    PreFilingScannerService,
    USCISApiService,
)

client = TestClient(app)


# ── Agentic Pipeline ──

class TestAgenticPipeline:
    def setup_method(self):
        self.svc = AgenticPipelineService()

    def test_create_pipeline(self):
        p = self.svc.create_pipeline("case-1", "H-1B", {"attorney_id": "atty-1"})
        assert p["case_id"] == "case-1"
        assert p["visa_type"] == "H-1B"
        assert p["status"] == "running"
        assert len(p["steps"]) == 8
        assert p["steps"][0]["status"] == "in_progress"

    def test_advance_pipeline(self):
        p = self.svc.create_pipeline("case-2", "H-1B", {})
        p2 = self.svc.advance_pipeline(p["id"])
        assert p2["steps"][0]["status"] in ("completed", "flagged")
        assert p2["steps"][1]["status"] == "in_progress"
        assert p2["current_step"] == 1

    def test_advance_all_steps(self):
        p = self.svc.create_pipeline("case-3", "O-1", {})
        for _ in range(8):
            p = self.svc.advance_pipeline(p["id"])
        assert p["status"] == "completed"

    def test_advance_nonexistent(self):
        with pytest.raises(ValueError):
            self.svc.advance_pipeline("fake-id")

    def test_list_pipelines(self):
        self.svc.create_pipeline("c1", "H-1B", {"attorney_id": "a1"})
        self.svc.create_pipeline("c2", "L-1", {"attorney_id": "a1"})
        self.svc.create_pipeline("c3", "O-1", {"attorney_id": "a2"})
        assert len(self.svc.list_pipelines("a1")) == 2

    def test_api_create_pipeline(self):
        resp = client.post("/api/pipeline", json={"case_id": "c1", "visa_type": "H-1B", "applicant_data": {}})
        assert resp.status_code == 201
        assert resp.json()["status"] == "running"

    def test_api_get_pipeline_404(self):
        resp = client.get("/api/pipeline/nonexistent")
        assert resp.status_code == 404


# ── H-1B Lottery Simulator ──

class TestH1BLottery:
    def setup_method(self):
        self.svc = H1BLotterySimulatorService()

    def test_simulate_level_1(self):
        result = self.svc.simulate({"wage_level": 1})
        assert result["selection_probability"] < 0.10
        assert result["wage_level"] == 1

    def test_simulate_level_4(self):
        result = self.svc.simulate({"wage_level": 4})
        assert result["selection_probability"] > 0.30

    def test_wage_weighting(self):
        r1 = self.svc.simulate({"wage_level": 1})
        r4 = self.svc.simulate({"wage_level": 4})
        assert r4["selection_probability"] > r1["selection_probability"] * 3

    def test_masters_bonus(self):
        r_no = self.svc.simulate({"wage_level": 2, "has_us_masters": False})
        r_yes = self.svc.simulate({"wage_level": 2, "has_us_masters": True})
        assert r_yes["selection_probability"] > r_no["selection_probability"]

    def test_batch_simulate(self):
        employees = [{"wage_level": i} for i in [1, 2, 3, 4]]
        result = self.svc.batch_simulate(employees)
        assert result["total_candidates"] == 4
        assert result["expected_selections"] > 0

    def test_historical_rates(self):
        rates = self.svc.get_historical_rates()
        assert "FY2027" in rates
        assert rates["FY2027"][4] > rates["FY2027"][1]

    def test_api_simulate(self):
        resp = client.post("/api/h1b-lottery/simulate", json={"wage_level": 3, "salary": 150000})
        assert resp.status_code == 200
        assert "selection_probability" in resp.json()

    def test_api_historical(self):
        resp = client.get("/api/h1b-lottery/historical")
        assert resp.status_code == 200


# ── EAD Gap Risk ──

class TestEADRisk:
    def setup_method(self):
        self.svc = EADGapRiskService()

    def test_critical_risk(self):
        result = self.svc.analyze_employee({"ead_expiry": "2026-04-01", "visa_type": "EAD"})
        assert result["risk_level"] in ("critical", "high")

    def test_low_risk(self):
        result = self.svc.analyze_employee({"ead_expiry": "2027-06-01", "visa_type": "EAD"})
        assert result["risk_level"] == "low"

    def test_no_ead(self):
        result = self.svc.analyze_employee({"visa_type": "H-1B"})
        assert result["risk_level"] == "none"

    def test_auto_extension_eliminated(self):
        result = self.svc.analyze_employee({"ead_expiry": "2026-08-01", "visa_type": "EAD"})
        assert result["auto_extension_eligible"] is False

    def test_workforce_analysis(self):
        employees = [
            {"id": "1", "visa_type": "EAD", "ead_expiry": "2026-04-01"},
            {"id": "2", "visa_type": "EAD", "ead_expiry": "2027-01-01"},
            {"id": "3", "visa_type": "H-1B"},
        ]
        results = self.svc.analyze_workforce(employees)
        assert len(results) == 2  # H-1B excluded
        assert results[0]["risk_level"] in ("critical", "high")  # Most urgent first

    def test_generate_renewals(self):
        renewals = self.svc.generate_renewals(["emp-1", "emp-2"])
        assert len(renewals) == 2
        assert renewals[0]["form"] == "I-765"

    def test_rules(self):
        rules = self.svc.get_auto_extension_rules()
        assert "eliminated" in rules["current_policy"].lower()

    def test_api_analyze(self):
        resp = client.post("/api/ead-risk/analyze", json={"ead_expiry": "2026-06-01", "visa_type": "EAD"})
        assert resp.status_code == 200

    def test_api_rules(self):
        resp = client.get("/api/ead-risk/rules")
        assert resp.status_code == 200


# ── Pre-Filing Scanner ──

class TestPreFilingScanner:
    def setup_method(self):
        self.svc = PreFilingScannerService()

    def test_clean_case(self):
        result = self.svc.scan_case({
            "visa_type": "H-1B",
            "applicant_name": "Wei Chen",
            "employer": "Tech Corp",
            "documents": ["passport", "degree", "resume", "offer_letter", "lca"],
        })
        assert result["overall_score"] >= 70
        assert result["pass_fail"] == "pass"

    def test_missing_docs(self):
        result = self.svc.scan_case({
            "visa_type": "H-1B",
            "applicant_name": "Wei Chen",
            "employer": "Tech Corp",
            "documents": ["passport"],
        })
        assert result["total_issues"] > 0
        assert any(i["category"] == "missing_document" for i in result["issues"])

    def test_prior_denial(self):
        result = self.svc.scan_case({
            "visa_type": "H-1B",
            "applicant_name": "Test",
            "employer": "Corp",
            "prior_denial": True,
        })
        assert any(i["category"] == "eligibility_issue" for i in result["issues"])

    def test_rfe_triggers(self):
        triggers = self.svc.get_common_rfe_triggers("H-1B")
        assert len(triggers) >= 5
        assert any("specialty" in t["trigger"].lower() for t in triggers)

    def test_scan_form(self):
        result = self.svc.scan_form({"name": "Wei Chen", "address": ""}, "I-129")
        assert not result["passed"]
        assert len(result["issues"]) == 1

    def test_api_scan(self):
        resp = client.post("/api/prefiling/scan", json={"visa_type": "H-1B", "applicant_name": "Test", "employer": "Corp"})
        assert resp.status_code == 200

    def test_api_rfe_triggers(self):
        resp = client.get("/api/prefiling/rfe-triggers/H-1B")
        assert resp.status_code == 200


# ── USCIS API ──

class TestUSCISApi:
    def setup_method(self):
        self.svc = USCISApiService()

    def test_get_status(self):
        result = self.svc.get_case_status("WAC2612345678")
        assert result["receipt_number"] == "WAC2612345678"
        assert result["form_type"] == "I-129"
        assert "history" in result

    def test_bulk_status(self):
        results = self.svc.bulk_status_check(["WAC123", "LIN456", "EAC789"])
        assert len(results) == 3

    def test_subscribe(self):
        result = self.svc.subscribe_to_updates("WAC123", "https://example.com/hook")
        assert result["status"] == "active"

    def test_processing_times(self):
        result = self.svc.get_processing_times("I-129")
        assert result["min_days"] < result["max_days"]

    def test_compare(self):
        result = self.svc.compare_to_average("WAC123")
        assert "percentile" in result

    def test_api_status(self):
        resp = client.get("/api/uscis/status/WAC2612345678")
        assert resp.status_code == 200
        assert resp.json()["form_type"] == "I-129"

    def test_api_processing_times(self):
        resp = client.get("/api/uscis/processing-times/I-485")
        assert resp.status_code == 200
