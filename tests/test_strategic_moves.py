"""Tests for the 16 strategic-move services shipped in this batch.

Single file covers all 16 to keep the test suite organized.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Approval Index
# ---------------------------------------------------------------------------

class TestApprovalIndex:
    def _svc(self):
        from immigration_compliance.services.approval_index_service import ApprovalIndexService
        return ApprovalIndexService()

    def test_record_outcome_basic(self):
        svc = self._svc()
        rec = svc.record_outcome(
            workspace_id="WS-1", visa_type="H-1B", country="US",
            outcome="approved", decision_date="2025-03-15",
            attorney_id="A1", service_center="VSC",
        )
        assert rec["outcome"] == "approved"

    def test_invalid_outcome_rejected(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.record_outcome(
                workspace_id="WS-1", visa_type="H-1B", country="US",
                outcome="bogus", decision_date="2025-03-15",
            )

    def test_privacy_floor_under_5(self):
        svc = self._svc()
        for i in range(3):
            svc.record_outcome(
                workspace_id=f"WS-{i}", visa_type="O-1A", country="US",
                outcome="approved", decision_date="2025-03-15",
                attorney_id="A1", service_center="TSC",
            )
        slice_ = svc.compute_slice(visa_type="O-1A", country="US")
        assert slice_["tier"] == "insufficient"
        assert slice_["publishable"] is False

    def test_compute_slice_with_volume(self):
        svc = self._svc()
        for i in range(180):
            svc.record_outcome(
                workspace_id=f"WS-{i}", visa_type="H-1B", country="US",
                outcome="approved", decision_date="2025-03-15",
                attorney_id="A1", service_center="VSC",
            )
        for i in range(20):
            svc.record_outcome(
                workspace_id=f"WS-D{i}", visa_type="H-1B", country="US",
                outcome="denied", decision_date="2025-03-15",
                attorney_id="A1", service_center="VSC",
            )
        slice_ = svc.compute_slice(visa_type="H-1B", country="US")
        assert slice_["case_count"] == 200
        assert slice_["tier"] in ("audited", "preliminary")
        assert 0.85 <= slice_["approval_rate"] <= 0.95

    def test_attorney_scorecard(self):
        svc = self._svc()
        for i in range(15):
            svc.record_outcome(
                workspace_id=f"WS-{i}", visa_type="H-1B", country="US",
                outcome="approved", decision_date="2025-04-01",
                attorney_id="A2", service_center="VSC",
            )
        card = svc.attorney_scorecard("A2")
        assert card["case_count"] == 15

    def test_list_outcomes_filtered(self):
        svc = self._svc()
        svc.record_outcome(workspace_id="WS-A", visa_type="H-1B", country="US",
                           outcome="approved", decision_date="2025-03-15",
                           attorney_id="A3")
        svc.record_outcome(workspace_id="WS-B", visa_type="L-1A", country="US",
                           outcome="approved", decision_date="2025-03-15",
                           attorney_id="A3")
        outcomes = svc.list_outcomes(attorney_id="A3", visa_type="H-1B")
        assert len(outcomes) == 1


# ---------------------------------------------------------------------------
# Outcome Telemetry
# ---------------------------------------------------------------------------

class TestOutcomeTelemetry:
    def _make(self):
        from immigration_compliance.services.approval_index_service import ApprovalIndexService
        from immigration_compliance.services.outcome_telemetry_service import (
            OutcomeTelemetryService,
        )
        ai = ApprovalIndexService()
        return ai, OutcomeTelemetryService(approval_index_service=ai)

    def test_privacy_floor(self):
        ai, ot = self._make()
        for i in range(8):
            ai.record_outcome(
                workspace_id=f"WS-{i}", visa_type="H-1B", country="US",
                outcome="approved", decision_date="2025-03-01",
                attorney_id=f"A{i}", attorney_fee_usd=4000.0,
            )
        stats = ot.compute_pricing_for_slice(visa_type="H-1B", country="US")
        assert stats["publishable"] is False

    def test_pricing_with_volume(self):
        ai, ot = self._make()
        for i in range(15):
            ai.record_outcome(
                workspace_id=f"WS-{i}", visa_type="H-1B", country="US",
                outcome="approved", decision_date="2025-03-15",
                attorney_id=f"A{i}", attorney_fee_usd=3000.0 + 100 * i,
                government_fee_usd=460.0,
            )
        stats = ot.compute_pricing_for_slice(visa_type="H-1B", country="US")
        assert stats["case_count"] == 15
        assert stats["publishable"] is True

    def test_applicant_pricing_estimate(self):
        ai, ot = self._make()
        for i in range(15):
            ai.record_outcome(
                workspace_id=f"WS-{i}", visa_type="H-1B", country="US",
                outcome="approved", decision_date="2025-03-15",
                attorney_fee_usd=3500.0, government_fee_usd=460.0,
            )
        est = ot.applicant_pricing_estimate(visa_type="H-1B", country="US")
        assert "estimate_available" in est


# ---------------------------------------------------------------------------
# Embassy Intel
# ---------------------------------------------------------------------------

class TestEmbassyIntel:
    def _svc(self):
        from immigration_compliance.services.embassy_intel_service import EmbassyIntelService
        return EmbassyIntelService()

    def test_seed_catalog_present(self):
        svc = self._svc()
        posts = svc.list_posts()
        assert len(posts) >= 10

    def test_search_by_country(self):
        svc = self._svc()
        us_posts = svc.list_posts(operates_for="US")
        assert len(us_posts) >= 1

    def test_submit_report(self):
        svc = self._svc()
        post_id = svc.list_posts()[0]["id"]
        r = svc.submit_report(
            post_id=post_id, kind="wait_time",
            body="Wait was 30 days", category_visa="H-1B",
            reporter_role="attorney",
        )
        assert r["weight"] == 3

    def test_invalid_post_rejected(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.submit_report(post_id="NOPE", kind="wait_time", body="x")


# ---------------------------------------------------------------------------
# Government Status Polling
# ---------------------------------------------------------------------------

class TestGovernmentPolling:
    def _svc(self):
        from immigration_compliance.services.government_status_polling_service import (
            GovernmentStatusPollingService,
        )
        return GovernmentStatusPollingService()

    def test_register_subscription(self):
        svc = self._svc()
        sub = svc.subscribe(
            receipt_number="MSC1234567890", agency="uscis",
            workspace_id="WS-1", attorney_id="A1",
        )
        assert sub["agency"] == "uscis"
        assert sub["active"] is True

    def test_invalid_agency_rejected(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.subscribe(receipt_number="X", agency="bogus")

    def test_unsubscribe(self):
        svc = self._svc()
        sub = svc.subscribe(receipt_number="MSC1", agency="uscis")
        assert svc.unsubscribe(sub["id"]) is True
        assert svc.unsubscribe("missing") is False


# ---------------------------------------------------------------------------
# Eligibility Checker
# ---------------------------------------------------------------------------

class TestEligibilityChecker:
    def _svc(self):
        from immigration_compliance.services.eligibility_checker_service import (
            EligibilityCheckerService,
        )
        return EligibilityCheckerService()

    def test_pathways_registered(self):
        svc = self._svc()
        pathways = svc.list_pathways()
        assert len(pathways) >= 5

    def test_evaluate_unknown_rejected(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.evaluate(pathway_id="bogus_pathway", answers={})

    def test_evaluate_returns_score(self):
        svc = self._svc()
        pathway = svc.list_pathways()[0]
        result = svc.evaluate(pathway_id=pathway["id"], answers={})
        assert "eligible" in result


# ---------------------------------------------------------------------------
# Lead Marketplace
# ---------------------------------------------------------------------------

class TestLeadMarketplace:
    def _svc(self):
        from immigration_compliance.services.lead_marketplace_service import (
            LeadMarketplaceService,
        )
        return LeadMarketplaceService()

    def test_list_complexity_tiers(self):
        svc = self._svc()
        tiers = svc.list_complexity_tiers()
        assert len(tiers) >= 3
        kinds = {t["tier"] for t in tiers}
        assert "standard" in kinds

    def test_list_brief_statuses(self):
        svc = self._svc()
        statuses = svc.list_brief_statuses()
        assert "open" in statuses
        assert "claimed" in statuses

    def test_no_intake_engine_fails(self):
        svc = self._svc()
        with pytest.raises(RuntimeError):
            svc.prepare_brief(applicant_id="A1", intake_session_id="S1")


# ---------------------------------------------------------------------------
# Outcome Reviews
# ---------------------------------------------------------------------------

class TestOutcomeReview:
    def _make(self):
        from immigration_compliance.services.approval_index_service import ApprovalIndexService
        from immigration_compliance.services.outcome_review_service import (
            OutcomeReviewService,
        )
        ai = ApprovalIndexService()
        return ai, OutcomeReviewService(approval_index_service=ai)

    def test_submit_review(self):
        ai, rv = self._make()
        ai.record_outcome(
            workspace_id="WS-1", visa_type="H-1B", country="US",
            outcome="approved", decision_date="2025-03-15", attorney_id="A1",
        )
        review = rv.submit_review(
            applicant_id="C1", attorney_id="A1",
            receipt_number="WS-1",
            ratings={"communication": 5, "knowledge": 5, "responsiveness": 4,
                     "value": 4, "outcome": 5},
        )
        assert review["rating_avg"] >= 4

    def test_rating_validation(self):
        _, rv = self._make()
        with pytest.raises(ValueError):
            rv.submit_review(
                applicant_id="C1", attorney_id="A1", receipt_number="W1",
                ratings={"communication": 9},
            )

    def test_unknown_facet_rejected(self):
        _, rv = self._make()
        with pytest.raises(ValueError):
            rv.submit_review(
                applicant_id="C1", attorney_id="A1", receipt_number="W1",
                ratings={"bogus_facet": 5},
            )


# ---------------------------------------------------------------------------
# Cadence Tracker
# ---------------------------------------------------------------------------

class TestCadenceTracker:
    def _svc(self):
        from immigration_compliance.services.cadence_tracker_service import (
            CadenceTrackerService,
        )
        return CadenceTrackerService()

    def test_enroll_workspace(self):
        svc = self._svc()
        e = svc.enroll(workspace_id="WS-1", attorney_id="A1")
        assert e["active"] is True
        assert e["status"] == "fresh"

    def test_record_update_resets_clock(self):
        svc = self._svc()
        svc.enroll(workspace_id="WS-1", attorney_id="A1")
        u = svc.record_update(workspace_id="WS-1", actor_id="A1",
                              body="Filed I-129 today")
        assert u["workspace_id"] == "WS-1"

    def test_response_health_score(self):
        svc = self._svc()
        svc.enroll(workspace_id="WS-1", attorney_id="A1")
        svc.record_update(workspace_id="WS-1", actor_id="A1", body="ok")
        health = svc.attorney_response_health("A1")
        assert "score" in health

    def test_disenroll(self):
        svc = self._svc()
        svc.enroll(workspace_id="WS-X", attorney_id="A1")
        rec = svc.disenroll(workspace_id="WS-X", reason="closed")
        assert rec["active"] is False


# ---------------------------------------------------------------------------
# SLA Tracker
# ---------------------------------------------------------------------------

class TestSlaTracker:
    def _svc(self):
        from immigration_compliance.services.sla_tracker_service import SlaTrackerService
        return SlaTrackerService()

    def test_start_sla(self):
        svc = self._svc()
        sla = svc.start(kind="lead_initial_contact", responsible_user_id="A1")
        assert sla["status"] == "open"

    def test_invalid_kind_rejected(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.start(kind="bogus", responsible_user_id="A1")

    def test_complete_sla(self):
        svc = self._svc()
        s = svc.start(kind="lead_initial_contact", responsible_user_id="A1")
        result = svc.complete(s["id"])
        assert result["status"] == "met"

    def test_attorney_sla_health(self):
        svc = self._svc()
        s = svc.start(kind="lead_initial_contact", responsible_user_id="A2")
        svc.complete(s["id"])
        h = svc.attorney_sla_health("A2")
        assert h["entry_count"] >= 1


# ---------------------------------------------------------------------------
# WhatsApp Channel
# ---------------------------------------------------------------------------

class TestWhatsAppChannel:
    def _svc(self):
        from immigration_compliance.services.whatsapp_channel_service import (
            WhatsAppChannelService,
        )
        return WhatsAppChannelService()

    def test_e164_validation(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.get_or_create_conversation(
                applicant_user_id="A1", phone_e164="not-a-number",
            )

    def test_get_or_create_conversation(self):
        svc = self._svc()
        c = svc.get_or_create_conversation(
            applicant_user_id="A1", phone_e164="+15551234567",
        )
        assert c["state"] == "active"

    def test_send_template(self):
        svc = self._svc()
        c = svc.get_or_create_conversation(
            applicant_user_id="A1", phone_e164="+15551234567",
        )
        msg = svc.send_template(
            convo_id=c["id"], template_kind="approval",
            variables={"visa_type": "H-1B"},
        )
        assert msg["template_kind"] == "approval"

    def test_template_missing_variable_rejected(self):
        svc = self._svc()
        c = svc.get_or_create_conversation(
            applicant_user_id="A1", phone_e164="+15551234567",
        )
        with pytest.raises(ValueError):
            svc.send_template(
                convo_id=c["id"], template_kind="case_status_update",
                variables={"visa_type": "H-1B"},  # missing receipt + status
            )

    def test_list_templates(self):
        svc = self._svc()
        templates = svc.list_templates()
        assert len(templates) >= 5


# ---------------------------------------------------------------------------
# Peer Network + CLE
# ---------------------------------------------------------------------------

class TestPeerNetwork:
    def _svc(self):
        from immigration_compliance.services.peer_network_service import PeerNetworkService
        return PeerNetworkService()

    def test_create_thread(self):
        svc = self._svc()
        t = svc.create_thread(
            author_user_id="A1", title="O-1A criteria question",
            body="Anyone seen this before?", kind="case_strategy",
        )
        assert t["kind"] == "case_strategy"

    def test_invalid_thread_kind(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.create_thread(author_user_id="A1", title="x", body="y",
                              kind="bogus")

    def test_record_cle_activity(self):
        svc = self._svc()
        rec = svc.record_activity(
            attorney_id="A1", kind="thread_authorship", minutes=30,
        )
        assert rec["credit_hours_earned"] > 0

    def test_cle_summary(self):
        svc = self._svc()
        svc.record_activity(attorney_id="A1", kind="thread_authorship",
                            minutes=60)
        summary = svc.attorney_cle_summary(attorney_id="A1", jurisdiction="NY")
        assert summary["credit_hours_earned"] > 0


# ---------------------------------------------------------------------------
# Industry Benchmark Report
# ---------------------------------------------------------------------------

class TestIndustryBenchmarkReport:
    def _svc(self):
        from immigration_compliance.services.benchmark_report_service import (
            BenchmarkReportService,
        )
        return BenchmarkReportService()

    def test_generate_report(self):
        svc = self._svc()
        report = svc.generate(kind="annual", title="2025 Industry",
                              period_label="2025", cover_summary="annual")
        assert report["kind"] == "annual"

    def test_render_text(self):
        svc = self._svc()
        report = svc.generate(kind="annual", title="2025", period_label="2025",
                              cover_summary="x")
        text = svc.render_text(report)
        assert "2025" in text


# ---------------------------------------------------------------------------
# Local Payments
# ---------------------------------------------------------------------------

class TestLocalPayments:
    def _svc(self):
        from immigration_compliance.services.local_payments_service import (
            LocalPaymentsService,
        )
        return LocalPaymentsService()

    def test_list_methods(self):
        svc = self._svc()
        methods = svc.list_methods()
        assert len(methods) >= 5

    def test_methods_for_country(self):
        svc = self._svc()
        methods = svc.methods_for_country("IN")
        assert isinstance(methods, list)

    def test_create_checkout_session(self):
        svc = self._svc()
        methods = svc.list_methods(country="IN")
        if not methods:
            pytest.skip("No IN methods")
        method = methods[0]
        sess = svc.create_checkout_session(
            method_id=method["id"], amount_minor_units=50000,
            currency=method["currencies"][0], intent="consultation_fee",
            applicant_user_id="C1",
        )
        assert sess["status"] in ("open", "failed")

    def test_iolta_compatibility_enforced(self):
        svc = self._svc()
        non_iolta = next(
            (m for m in svc.list_methods() if not m.get("iolta_compatible")),
            None,
        )
        if non_iolta is None:
            pytest.skip("No non-IOLTA method to test")
        with pytest.raises(ValueError):
            svc.create_checkout_session(
                method_id=non_iolta["id"], amount_minor_units=50000,
                currency=non_iolta["currencies"][0],
                intent="retainer",
            )


# ---------------------------------------------------------------------------
# SOC 2 Audit
# ---------------------------------------------------------------------------

class TestSoc2Audit:
    def _svc(self):
        from immigration_compliance.services.soc2_audit_service import Soc2AuditService
        return Soc2AuditService()

    def test_controls_registered(self):
        svc = self._svc()
        controls = svc.list_controls()
        assert len(controls) >= 15

    def test_trust_service_criteria_coverage(self):
        svc = self._svc()
        criteria = svc.list_trust_service_criteria()
        assert {"security", "availability", "confidentiality"} <= set(criteria)

    def test_evidence_pack(self):
        svc = self._svc()
        pack = svc.generate_evidence_pack(
            period_start="2025-01-01", period_end="2025-03-31",
        )
        assert pack["period_start"] == "2025-01-01"
        assert pack["control_count"] >= 15

    def test_log_incident(self):
        svc = self._svc()
        i = svc.log_incident(
            incident_type="access_control",
            severity="medium",
            description="Test incident",
            actor_user_id="A1",
        )
        assert i["severity"] == "medium"


# ---------------------------------------------------------------------------
# Bar Endorsements
# ---------------------------------------------------------------------------

class TestBarEndorsement:
    def _svc(self):
        from immigration_compliance.services.bar_endorsement_service import (
            BarEndorsementService,
        )
        return BarEndorsementService()

    def test_record_endorsement(self):
        svc = self._svc()
        e = svc.record_endorsement(
            bar_jurisdiction="ca", bar_full_name="State Bar of California",
            endorsement_type="advisory_opinion",
            issued_date="2025-01-15",
            scope=["client_intake", "form_population"],
        )
        assert e["bar_jurisdiction"] == "CA"

    def test_invalid_endorsement_type(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.record_endorsement(
                bar_jurisdiction="CA", bar_full_name="x",
                endorsement_type="bogus", issued_date="2025-01-15",
                scope=["x"],
            )

    def test_safe_harbor_lookup(self):
        svc = self._svc()
        svc.record_endorsement(
            bar_jurisdiction="NY", bar_full_name="NYSBA",
            endorsement_type="no_action_letter",
            issued_date="2025-02-01",
            scope=["client_intake"],
        )
        result = svc.is_attorney_safe_harbor_covered("NY", scope="client_intake")
        assert result["covered"] is True

    def test_application_pipeline(self):
        svc = self._svc()
        app = svc.open_application(
            bar_jurisdiction="TX", bar_full_name="State Bar of Texas",
            endorsement_type_target="advisory_opinion",
            scope_target=["form_population"],
        )
        result = svc.transition_stage(app["id"], "submitted",
                                       note="Filed today")
        assert result["stage"] == "submitted"

    def test_coverage_matrix(self):
        svc = self._svc()
        svc.record_endorsement(
            bar_jurisdiction="WA", bar_full_name="WSBA",
            endorsement_type="advisory_opinion", issued_date="2025-01-01",
            scope=["x"],
        )
        m = svc.coverage_matrix()
        assert "WA" in m["covered_jurisdictions"]


# ---------------------------------------------------------------------------
# Malpractice Partner
# ---------------------------------------------------------------------------

class TestMalpracticePartner:
    def _svc(self):
        from immigration_compliance.services.malpractice_partner_service import (
            MalpracticePartnerService,
        )
        return MalpracticePartnerService()

    def test_register_partner(self):
        svc = self._svc()
        p = svc.register_partner(
            carrier_name="ALAS", contact_name="Jane Doe",
            contact_email="jane@alas.com", discount_pct=10.0,
            eligibility_criteria=["verified_attorney", "no_active_complaints"],
            coverage_scope="immigration_law",
            agreement_signed_date="2025-01-15",
        )
        assert p["carrier_name"] == "ALAS"
        assert p["status"] == "signed"

    def test_invalid_discount(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.register_partner(
                carrier_name="x", contact_name="y", contact_email="y@x.com",
                discount_pct=150, eligibility_criteria=[],
                coverage_scope="x",
            )

    def test_invalid_criterion(self):
        svc = self._svc()
        with pytest.raises(ValueError):
            svc.register_partner(
                carrier_name="x", contact_name="y", contact_email="y@x.com",
                discount_pct=10, eligibility_criteria=["bogus"],
                coverage_scope="x",
            )

    def test_eligibility_evaluation_default_met(self):
        svc = self._svc()
        p = svc.register_partner(
            carrier_name="Aon", contact_name="X", contact_email="x@a.com",
            discount_pct=12,
            eligibility_criteria=["trust_accounting_enabled", "no_active_complaints"],
            coverage_scope="x",
        )
        result = svc.evaluate_attorney_eligibility("ATT-1", p["id"])
        assert result["eligible"] is True

    def test_enrollment_blocks_when_ineligible(self):
        svc = self._svc()
        p = svc.register_partner(
            carrier_name="Mercer", contact_name="X", contact_email="x@m.com",
            discount_pct=8,
            eligibility_criteria=["verified_attorney"],
            coverage_scope="x",
        )
        with pytest.raises(ValueError):
            svc.enroll_attorney(attorney_id="A1", partner_id=p["id"])

    def test_list_eligibility_kinds(self):
        from immigration_compliance.services.malpractice_partner_service import (
            MalpracticePartnerService,
        )
        kinds = MalpracticePartnerService.list_eligibility_kinds()
        assert "verified_attorney" in kinds
