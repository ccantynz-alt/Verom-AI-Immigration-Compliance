"""Tests for competitive gap-closing features."""

from __future__ import annotations

import pytest

from immigration_compliance.services.hris_deep_service import HRISDeepService, LifecycleEvent
from immigration_compliance.services.benchmarking_service import BenchmarkingService
from immigration_compliance.services.flat_rate_service import FlatRateService, PricingModel
from immigration_compliance.services.uscis_client_service import USCISClientService


# ============================
# HRIS Deep Integration Tests
# ============================

class TestHRISDeepService:

    def setup_method(self):
        self.svc = HRISDeepService()

    def test_new_hire_lifecycle_event(self):
        event = {
            "event_type": "new_hire",
            "employee_id": "emp-001",
            "first_name": "Wei",
            "last_name": "Zhang",
            "country_of_citizenship": "China",
            "visa_type": "H-1B",
            "hire_date": "2026-04-01",
        }
        result = self.svc.handle_lifecycle_event(event)
        assert result["event_type"] == "new_hire"
        assert result["immigration_impact"]["severity"] == "high"
        assert len(result["actions_required"]) >= 2
        assert any(a["action"] == "complete_i9" for a in result["actions_required"])

    def test_termination_visa_holder_generates_alert(self):
        event = {
            "event_type": "termination",
            "employee_id": "emp-002",
            "visa_type": "H-1B",
        }
        result = self.svc.handle_lifecycle_event(event)
        assert result["immigration_impact"]["severity"] == "critical"
        alerts = self.svc.get_payroll_immigration_alerts()
        assert any(a["alert_type"] == "termination_visa_holder" for a in alerts)

    def test_us_citizen_new_hire_no_immigration_impact(self):
        event = {
            "event_type": "new_hire",
            "employee_id": "emp-003",
            "country_of_citizenship": "US",
        }
        result = self.svc.handle_lifecycle_event(event)
        assert result["immigration_impact"]["severity"] == "none"

    def test_compensation_change_h1b_requires_wage_check(self):
        event = {
            "event_type": "compensation_change",
            "employee_id": "emp-004",
            "visa_type": "H-1B",
            "new_salary": 120000,
        }
        result = self.svc.handle_lifecycle_event(event)
        assert result["immigration_impact"]["severity"] == "high"
        assert any(a["action"] == "verify_prevailing_wage" for a in result["actions_required"])

    def test_location_change_h1b_requires_lca_check(self):
        event = {
            "event_type": "location_change",
            "employee_id": "emp-005",
            "visa_type": "H-1B",
        }
        result = self.svc.handle_lifecycle_event(event)
        assert result["immigration_impact"]["severity"] == "high"
        assert any(a["action"] == "check_msa_change" for a in result["actions_required"])

    def test_screen_new_hire_h1b(self):
        result = self.svc.screen_new_hire({
            "first_name": "Priya",
            "last_name": "Sharma",
            "country_of_citizenship": "India",
            "visa_type": "H-1B",
            "previous_employer": "TechCorp",
        })
        assert result["risk_level"] == "high"
        assert result["sponsorship_assessment"]["transfer_required"] is True
        assert result["i9_required"] is True

    def test_screen_new_hire_opt(self):
        result = self.svc.screen_new_hire({
            "first_name": "Jun",
            "last_name": "Li",
            "country_of_citizenship": "China",
            "visa_type": "OPT",
            "stem_eligible": True,
        })
        assert result["sponsorship_assessment"]["stem_extension_eligible"] is True
        assert result["sponsorship_assessment"]["h1b_sponsorship_recommended"] is True

    def test_deel_import(self):
        deel_data = [
            {"employee_id": "d-001", "first_name": "Alice", "last_name": "Smith", "email": "a@co.com", "nationality": "UK", "visa_type": "H-1B"},
            {"id": "d-002", "legal_first_name": "Bob", "legal_last_name": "Jones", "work_email": "b@co.com", "citizenship": "Canada", "work_permit_type": "TN"},
        ]
        result = self.svc.import_from_deel(deel_data)
        assert result["imported"] == 2
        assert result["errors"] == 0
        assert result["employees"][0]["source"] == "deel_import"

    def test_workforce_snapshot(self):
        result = self.svc.get_workforce_immigration_snapshot("company-1")
        assert "summary" in result
        assert "visa_distribution" in result
        assert "compliance_score" in result

    def test_event_log(self):
        self.svc.handle_lifecycle_event({"event_type": "new_hire", "employee_id": "emp-100", "country_of_citizenship": "US"})
        self.svc.handle_lifecycle_event({"event_type": "termination", "employee_id": "emp-101", "visa_type": "L-1A"})
        log = self.svc.get_event_log()
        assert len(log) == 2
        log_filtered = self.svc.get_event_log("emp-100")
        assert len(log_filtered) == 1


# ============================
# Benchmarking Service Tests
# ============================

class TestBenchmarkingService:

    def setup_method(self):
        self.svc = BenchmarkingService()

    def test_platform_benchmarks_structure(self):
        result = self.svc.get_platform_benchmarks()
        assert "per_case_metrics" in result
        assert "weekly_metrics" in result
        assert "annual_metrics" in result
        assert "task_breakdown" in result
        assert "methodology" in result

    def test_time_reduction_is_significant(self):
        result = self.svc.get_platform_benchmarks()
        # Must show significant reduction to compete with LegalBridge's 60% claim
        assert result["per_case_metrics"]["percentage_reduction"] > 60

    def test_annual_savings_are_meaningful(self):
        result = self.svc.get_platform_benchmarks()
        assert result["annual_metrics"]["hours_saved_per_year"] > 500
        assert result["annual_metrics"]["billable_value_recovered"] > 100000

    def test_competitor_comparison(self):
        result = self.svc.get_competitor_comparison()
        assert "verom" in result
        assert "competitors" in result
        assert result["verom"]["verifiable"] is True
        assert result["competitors"]["legalbridge_ai"]["verifiable"] is False

    def test_firm_roi_calculation(self):
        result = self.svc.calculate_firm_roi({
            "num_attorneys": 5,
            "cases_per_week": 4,
            "avg_billable_rate": 400,
        })
        assert result["projected_savings"]["hours_saved_per_year"] > 0
        assert result["projected_savings"]["billable_value_per_year"] > 0
        assert result["firm_profile"]["attorneys"] == 5

    def test_task_logging(self):
        log = self.svc.log_task_completion({
            "task_type": "client_intake",
            "case_id": "case-1",
            "attorney_id": "att-1",
            "duration_minutes": 45,
        })
        assert log["task_type"] == "client_intake"
        metrics = self.svc.get_aggregate_metrics()
        assert metrics["total_tasks_logged"] == 1


# ============================
# Flat Rate Service Tests
# ============================

class TestFlatRateService:

    def setup_method(self):
        self.svc = FlatRateService()

    def test_get_package_templates(self):
        templates = self.svc.get_package_templates()
        assert len(templates) >= 6
        assert any(t["visa_type"] == "H-1B" for t in templates)

    def test_filter_templates_by_visa(self):
        h1b = self.svc.get_package_templates("H-1B")
        assert all("H-1B" in t["visa_type"] for t in h1b)
        assert len(h1b) >= 2  # standard + premium

    def test_create_attorney_package(self):
        pkg = self.svc.create_attorney_package("att-1", {
            "name": "My H-1B Package",
            "visa_type": "H-1B",
            "pricing_model": "flat_rate",
            "price_display": "Contact for quote",
            "included_services": ["Full H-1B filing"],
            "is_published": True,
        })
        assert pkg["attorney_id"] == "att-1"
        assert pkg["is_published"] is True

    def test_published_packages_visible(self):
        self.svc.create_attorney_package("att-1", {"name": "Pkg 1", "visa_type": "H-1B", "is_published": True})
        self.svc.create_attorney_package("att-1", {"name": "Pkg 2", "visa_type": "O-1A", "is_published": False})
        published = self.svc.get_published_packages()
        assert len(published) == 1

    def test_create_engagement_with_milestones(self):
        pkg = self.svc.create_attorney_package("att-1", {"name": "H-1B Pkg", "visa_type": "H-1B", "is_published": True})
        engagement = self.svc.create_engagement(pkg["id"], "app-1", "att-1")
        assert engagement["status"] == "pending_payment"
        assert len(engagement["milestones"]) == 4  # H-1B has 4 milestones

    def test_advance_milestone(self):
        pkg = self.svc.create_attorney_package("att-1", {"name": "H-1B Pkg", "visa_type": "H-1B"})
        eng = self.svc.create_engagement(pkg["id"], "app-1", "att-1")
        updated = self.svc.advance_milestone(eng["id"], 1)
        assert updated["milestones"][0]["status"] == "completed"

    def test_green_card_has_5_milestones(self):
        pkg = self.svc.create_attorney_package("att-1", {"name": "GC Pkg", "visa_type": "Green Card (EB-2)"})
        eng = self.svc.create_engagement(pkg["id"], "app-1", "att-1")
        assert len(eng["milestones"]) == 5

    def test_pricing_model_comparison(self):
        comparison = self.svc.compare_pricing_models()
        assert "flat_rate" in comparison
        assert "hourly" in comparison
        assert "milestone" in comparison
        assert "verom_recommendation" in comparison


# ============================
# USCIS Client Service Tests
# ============================

class TestUSCISClientService:

    def setup_method(self):
        self.svc = USCISClientService()

    def test_valid_receipt_number(self):
        result = self.svc.validate_receipt_number("WAC2390123456")
        assert result["is_valid"] is True
        assert result["service_center"] == "California Service Center"

    def test_invalid_receipt_number(self):
        result = self.svc.validate_receipt_number("INVALID123")
        assert result["is_valid"] is False
        assert result["error"] is not None

    def test_receipt_with_dashes_cleaned(self):
        result = self.svc.validate_receipt_number("WAC-239-012-3456")
        assert result["is_valid"] is True
        assert result["receipt_number"] == "WAC2390123456"

    def test_get_case_status(self):
        result = self.svc.get_case_status("WAC2390123456")
        assert "receipt_number" in result
        assert "status" in result
        assert result["status"]["code"] in [
            "received", "accepted", "fingerprint_scheduled", "fingerprint_taken",
            "rfe_sent", "rfe_received", "interview_scheduled", "approved",
            "denied", "withdrawn", "card_produced", "card_mailed", "card_delivered",
        ]

    def test_case_status_caching(self):
        result1 = self.svc.get_case_status("LIN2390123456")
        result2 = self.svc.get_case_status("LIN2390123456")
        assert result2["from_cache"] is True

    def test_bulk_status_check(self):
        receipts = ["WAC2390123456", "LIN2390123456", "EAC2390123456"]
        result = self.svc.bulk_status_check(receipts)
        assert result["total_requested"] == 3
        assert result["processed"] == 3

    def test_invalid_receipt_in_bulk(self):
        receipts = ["WAC2390123456", "INVALID"]
        result = self.svc.bulk_status_check(receipts)
        assert result["errors"] == 1

    def test_processing_times(self):
        result = self.svc.get_processing_times("I-129")
        assert result is not None
        assert result["min_days"] == 30
        assert result["premium_processing_available"] is True

    def test_all_processing_times(self):
        result = self.svc.get_all_processing_times()
        assert len(result) >= 10

    def test_subscribe_to_updates(self):
        sub = self.svc.subscribe_to_updates("WAC2390123456", email="test@example.com")
        assert sub["active"] is True
        assert sub["receipt_number"] == "WAC2390123456"

    def test_get_subscriptions(self):
        self.svc.subscribe_to_updates("WAC2390123456")
        self.svc.subscribe_to_updates("LIN2390123456")
        all_subs = self.svc.get_subscriptions()
        assert len(all_subs) == 2
        filtered = self.svc.get_subscriptions("WAC2390123456")
        assert len(filtered) == 1

    def test_status_categories(self):
        cats = self.svc.get_status_categories()
        assert len(cats) >= 10
        assert any(c["code"] == "approved" for c in cats)

    def test_ioe_receipt_prefix(self):
        result = self.svc.validate_receipt_number("IOE2390123456")
        assert result["is_valid"] is True
        assert result["service_center"] == "USCIS Electronic Immigration System (ELIS)"
