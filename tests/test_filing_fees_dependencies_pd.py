"""Tests for the filing-fee calculator, case dependency tracker, and priority
date forecaster."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Filing Fee Calculator
# ---------------------------------------------------------------------------

class TestFilingFeeCalculator:
    def _svc(self):
        from immigration_compliance.services.filing_fee_calculator_service import (
            FilingFeeCalculatorService,
        )
        return FilingFeeCalculatorService()

    def test_list_forms_includes_core(self):
        svc = self._svc()
        forms = svc.list_forms()
        for f in ("I-129", "I-130", "I-140", "I-485", "I-765", "N-400"):
            assert f in forms

    def test_list_agencies(self):
        svc = self._svc()
        agencies = svc.list_agencies()
        assert "USCIS" in agencies
        assert "DOL" in agencies
        assert "DOS" in agencies

    def test_lookup_h1b_schedule(self):
        svc = self._svc()
        s = svc.lookup_schedule(form="I-129", category="H-1B (named beneficiary)")
        assert s is not None
        assert s["filing_fee_usd"] == 780

    def test_lookup_unknown_returns_none(self):
        svc = self._svc()
        assert svc.lookup_schedule(form="ZZZ-999") is None

    def test_calculate_h1b_standard_employer(self):
        svc = self._svc()
        r = svc.calculate(
            form="I-129", category="H-1B (named beneficiary)",
            employer_size="standard",
        )
        # 780 + 600 asylum program fee = 1380
        assert r["total_usd"] == 1380
        labels = [li["label"] for li in r["line_items"]]
        assert any("filing fee" in l for l in labels)
        assert any("Asylum Program Fee" in l for l in labels)

    def test_calculate_h1b_small_employer(self):
        svc = self._svc()
        r = svc.calculate(
            form="I-129", category="H-1B (named beneficiary)",
            employer_size="small",
        )
        # 780 + 300 = 1080
        assert r["total_usd"] == 1080

    def test_calculate_h1b_with_premium_processing(self):
        svc = self._svc()
        r = svc.calculate(
            form="I-129", category="H-1B (named beneficiary)",
            employer_size="standard", with_premium_processing=True,
        )
        # 780 + 600 + 2805 = 4185
        assert r["total_usd"] == 4185

    def test_calculate_i130_online(self):
        svc = self._svc()
        r = svc.calculate(form="I-130", filed_online=True)
        assert r["total_usd"] == 625

    def test_calculate_i485_under_14(self):
        svc = self._svc()
        r = svc.calculate(form="I-485", applicant_age=10)
        assert r["total_usd"] == 950

    def test_calculate_i765_with_485(self):
        svc = self._svc()
        r = svc.calculate(form="I-765", category="Initial EAD",
                          filed_with_i485=True)
        assert r["total_usd"] == 260

    def test_fee_waiver_zeros_total(self):
        svc = self._svc()
        r = svc.calculate(form="N-400", fee_waiver_eligible=True)
        assert r["total_usd"] == 0

    def test_unknown_form_raises(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.calculate(form="BOGUS-999")

    def test_invalid_employer_size(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.calculate(form="I-129", employer_size="bogus")

    def test_calculate_bundle_family(self):
        svc = self._svc()
        # I-130 + I-485 + I-765 (concurrent) + I-131 (concurrent) for one beneficiary
        bundle = svc.calculate_bundle(forms=[
            {"form": "I-130", "filed_online": True},
            {"form": "I-485"},
            {"form": "I-765", "category": "Initial EAD", "filed_with_i485": True},
            {"form": "I-131", "category": "Advance Parole", "filed_with_i485": True},
        ])
        # 625 + 1440 + 260 + 630 = 2955
        assert bundle["total_usd"] == 2955
        assert bundle["form_count"] == 4

    def test_eoir26_appeal_fee(self):
        svc = self._svc()
        r = svc.calculate(form="EOIR-26", category="BIA Appeal")
        assert r["total_usd"] == 800
        assert r["agency"] == "EOIR"


# ---------------------------------------------------------------------------
# Case Dependency Service
# ---------------------------------------------------------------------------

class TestCaseDependency:
    def _svc(self):
        from immigration_compliance.services.case_dependency_service import (
            CaseDependencyService,
        )
        return CaseDependencyService()

    def test_list_kinds(self):
        from immigration_compliance.services.case_dependency_service import (
            CaseDependencyService,
        )
        kinds = CaseDependencyService.list_dependency_kinds()
        assert "blocking_approval" in kinds
        assert "priority_date_current" in kinds

    def test_list_templates(self):
        from immigration_compliance.services.case_dependency_service import (
            CaseDependencyService,
        )
        templates = CaseDependencyService.list_templates()
        assert "EB-2-PERM" in templates
        assert "I-130-AOS" in templates

    def test_get_template(self):
        from immigration_compliance.services.case_dependency_service import (
            CaseDependencyService,
        )
        t = CaseDependencyService.get_template("EB-2-PERM")
        assert t is not None
        assert any(e["predecessor"] == "ETA-9089" for e in t)

    def test_add_edge(self):
        svc = self._svc()
        e = svc.add_edge(
            workspace_id="WS-1", predecessor_form="I-140",
            dependent_form="I-485", kind="blocking_approval",
        )
        assert e["status"] == "pending"

    def test_invalid_kind(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.add_edge(workspace_id="WS-1", predecessor_form="I-140",
                         dependent_form="I-485", kind="bogus")

    def test_apply_template(self):
        svc = self._svc()
        edges = svc.apply_template(workspace_id="WS-1", template_name="EB-2-PERM")
        assert len(edges) >= 4

    def test_apply_unknown_template_raises(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.apply_template(workspace_id="WS-1", template_name="bogus")

    def test_resolve_predecessor(self):
        svc = self._svc()
        svc.add_edge(workspace_id="WS-1", predecessor_form="I-140",
                     dependent_form="I-485", kind="blocking_approval")
        unblocked = svc.mark_predecessor_satisfied(
            workspace_id="WS-1", predecessor_form="I-140",
            reason="I-140 approved",
        )
        assert len(unblocked) == 1
        assert unblocked[0]["status"] == "unblocked"

    def test_priority_date_requires_explicit_currentness(self):
        svc = self._svc()
        svc.add_edge(workspace_id="WS-1", predecessor_form="I-140",
                     dependent_form="I-485", kind="priority_date_current")
        # Resolving I-140 alone should NOT unblock the priority-date edge
        out = svc.mark_predecessor_satisfied(
            workspace_id="WS-1", predecessor_form="I-140",
        )
        assert len(out) == 0
        out2 = svc.mark_priority_date_current(workspace_id="WS-1")
        assert len(out2) == 1

    def test_ready_to_file_blocked(self):
        svc = self._svc()
        svc.apply_template(workspace_id="WS-1", template_name="EB-2-PERM")
        result = svc.ready_to_file("WS-1")
        # Initially everything downstream is blocked
        blocked_forms = {b["form"] for b in result["blocked"]}
        assert "I-140" in blocked_forms or "I-485" in blocked_forms

    def test_ready_to_file_after_unblock(self):
        svc = self._svc()
        svc.add_edge(workspace_id="WS-1", predecessor_form="I-140",
                     dependent_form="I-485", kind="blocking_approval")
        svc.mark_predecessor_satisfied(workspace_id="WS-1",
                                        predecessor_form="I-140")
        result = svc.ready_to_file("WS-1")
        ready_forms = {r["form"] for r in result["ready"]}
        assert "I-485" in ready_forms

    def test_remove_edge(self):
        svc = self._svc()
        e = svc.add_edge(workspace_id="WS-1", predecessor_form="I-140",
                         dependent_form="I-485", kind="blocking_approval")
        assert svc.remove_edge(e["id"]) is True
        assert svc.remove_edge("missing") is False


# ---------------------------------------------------------------------------
# Priority Date Forecaster
# ---------------------------------------------------------------------------

class TestPriorityDateForecaster:
    def _svc(self):
        from immigration_compliance.services.priority_date_forecaster_service import (
            PriorityDateForecasterService,
        )
        return PriorityDateForecasterService()

    def test_list_categories(self):
        from immigration_compliance.services.priority_date_forecaster_service import (
            PriorityDateForecasterService,
        )
        cats = PriorityDateForecasterService.list_categories()
        assert "EB-2" in cats
        assert "F2A" in cats

    def test_list_history_filtered(self):
        svc = self._svc()
        hist = svc.list_history(category="EB-2", chargeability="India")
        assert len(hist) >= 5

    def test_compute_velocity_eb2_aos(self):
        svc = self._svc()
        v = svc.compute_velocity(category="EB-2", chargeability="All Other")
        assert v["velocity_days_per_month_median"] is not None
        assert v["velocity_days_per_month_median"] > 0
        assert v["stable"] is True

    def test_compute_velocity_eb2_india(self):
        svc = self._svc()
        v = svc.compute_velocity(category="EB-2", chargeability="India")
        # India EB-2 moves slowly but consistently
        assert v["velocity_days_per_month_median"] is not None

    def test_forecast_already_current(self):
        svc = self._svc()
        out = svc.forecast(
            category="EB-1", chargeability="All Other",
            priority_date="2020-01-15",
        )
        # EB-1 All Other is current → priority date is already current
        assert out["currently_current"] is True

    def test_forecast_eb2_aos_pending(self):
        svc = self._svc()
        out = svc.forecast(
            category="EB-2", chargeability="All Other",
            priority_date="2024-12-01",
        )
        # 2024-12-01 is not yet reached by latest FAD ~ 2023-09-01
        assert out["forecast_status"] in ("projected", "unstable_history",
                                          "retrogressed_or_stalled")

    def test_forecast_unknown_category_raises(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.forecast(category="ZZZ", chargeability="India",
                         priority_date="2020-01-01")

    def test_forecast_unknown_chargeability_raises(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.forecast(category="EB-2", chargeability="Atlantis",
                         priority_date="2020-01-01")

    def test_record_bulletin_month(self):
        svc = self._svc()
        rec = svc.record_bulletin_month(
            bulletin_month="2025-05-01", category="EB-2",
            chargeability="All Other", final_action_date="2023-10-01",
        )
        assert rec["bulletin_month"] == "2025-05-01"

    def test_record_invalid_category_raises(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.record_bulletin_month(
                bulletin_month="2025-05-01", category="ZZZ",
                chargeability="All Other", final_action_date="2023-10-01",
            )

    def test_forecast_disclosure_present(self):
        svc = self._svc()
        out = svc.forecast(
            category="EB-2", chargeability="All Other",
            priority_date="2024-12-01",
        )
        assert "disclosure" in out
