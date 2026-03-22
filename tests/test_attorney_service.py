"""Tests for attorney portal services — profiles, intake, forms, deadlines, messaging, reports."""

import sys
sys.path.insert(0, "src")

from immigration_compliance.services.attorney_service import AttorneyService
from immigration_compliance.services.government_service import GovernmentPortalService
from immigration_compliance.services.marketplace_service import MarketplaceService
from immigration_compliance.services.ai_engine_service import AIEngineService
from immigration_compliance.services.everify_service import EVerifyService
from immigration_compliance.services.integration_service import IntegrationService
from immigration_compliance.services.market_intel_service import MarketIntelService

import pytest


# ── Attorney Service ──

class TestAttorneyProfile:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_create_profile(self):
        p = self.svc.create_profile("a1", {"firm_name": "Park Law", "specializations": ["H-1B", "O-1"]})
        assert p["id"] == "a1"
        assert p["firm_name"] == "Park Law"
        assert "H-1B" in p["specializations"]

    def test_get_profile(self):
        self.svc.create_profile("a1", {"firm_name": "Test"})
        p = self.svc.get_profile("a1")
        assert p is not None
        assert p["firm_name"] == "Test"

    def test_update_profile(self):
        self.svc.create_profile("a1", {"firm_name": "Old"})
        p = self.svc.update_profile("a1", {"firm_name": "New"})
        assert p["firm_name"] == "New"

    def test_search_attorneys(self):
        self.svc.create_profile("a1", {"jurisdictions": ["US"], "specializations": ["H-1B"]})
        self.svc.create_profile("a2", {"jurisdictions": ["UK"], "specializations": ["Skilled Worker"]})
        results = self.svc.search_attorneys({"country": "US"})
        assert len(results) == 1

    def test_get_stats(self):
        self.svc.create_profile("a1", {})
        stats = self.svc.get_attorney_stats("a1")
        assert "active_cases" in stats
        assert "approval_rate" in stats


class TestClientIntake:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_generate_intake_form(self):
        form = self.svc.generate_intake_form("H-1B", "US")
        assert form["visa_type"] == "H-1B"
        assert len(form["questions"]) > 8  # base + H-1B specific

    def test_submit_intake(self):
        form = self.svc.generate_intake_form("H-1B")
        result = self.svc.submit_intake(form["id"], {"full_name": "Test User"})
        assert result["status"] == "completed"

    def test_intake_to_case(self):
        form = self.svc.generate_intake_form("H-1B")
        self.svc.submit_intake(form["id"], {"full_name": "Maria Santos"})
        case = self.svc.intake_to_case(form["id"])
        assert case["client_name"] == "Maria Santos"
        assert case["visa_type"] == "H-1B"

    def test_intake_to_case_not_found(self):
        with pytest.raises(ValueError):
            self.svc.intake_to_case("nonexistent")


class TestCaseNotes:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_add_and_get_notes(self):
        note = self.svc.add_case_note("c1", "Client called", True, "a1")
        assert note["content"] == "Client called"
        notes = self.svc.get_case_notes("c1")
        assert len(notes) == 1

    def test_timeline_from_notes(self):
        self.svc.add_case_note("c1", "Note 1", True, "a1")
        timeline = self.svc.get_case_timeline("c1")
        assert len(timeline) == 1
        assert timeline[0]["event_type"] == "note_added"


class TestRFE:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_track_rfe(self):
        rfe = self.svc.track_rfe("c1", {"category": "evidence", "description": "Need more docs"})
        assert rfe["response_status"] == "pending"
        assert rfe["case_id"] == "c1"

    def test_generate_rfe_draft(self):
        rfe = self.svc.track_rfe("c1", {"category": "specialty_occupation"})
        draft = self.svc.generate_rfe_draft(rfe["id"])
        assert "Request for Evidence" in draft
        assert len(draft) > 100

    def test_update_rfe_status(self):
        rfe = self.svc.track_rfe("c1", {})
        updated = self.svc.update_rfe_status(rfe["id"], "submitted", "Final response text")
        assert updated["response_status"] == "submitted"
        assert updated["final_response"] == "Final response text"


class TestFormsLibrary:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_forms_library_count(self):
        forms = self.svc.get_forms_library()
        assert len(forms) >= 36

    def test_filter_by_country(self):
        us_forms = self.svc.get_forms_library(country="US")
        uk_forms = self.svc.get_forms_library(country="UK")
        assert len(us_forms) > len(uk_forms)

    def test_get_specific_form(self):
        form = self.svc.get_form("I-130")
        assert form is not None
        assert form["title"] == "Petition for Alien Relative"

    def test_auto_fill_form(self):
        filled = self.svc.auto_fill_form("I-129", {"client_name": "Test", "employer": "Acme"})
        assert filled["form_number"] == "I-129"
        assert filled["status"] == "draft"

    def test_required_forms(self):
        required = self.svc.get_required_forms("H-1B")
        assert "G-28" in required
        assert "I-129" in required

    def test_batch_generate(self):
        batch = self.svc.batch_generate_forms({"name": "Test"}, ["I-130", "I-485"])
        assert len(batch) == 2


class TestDeadlines:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_calculate_deadlines(self):
        deadlines = self.svc.calculate_deadlines("c1")
        assert len(deadlines) == 3

    def test_create_deadline(self):
        d = self.svc.create_deadline("c1", {"title": "File petition", "date": "2026-05-01"})
        assert d["case_id"] == "c1"

    def test_export_ical(self):
        self.svc.calculate_deadlines("c1")
        ical = self.svc.export_calendar_ical()
        assert "VCALENDAR" in ical
        assert "VEVENT" in ical


class TestCommunication:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_send_message(self):
        msg = self.svc.send_message("c1", "a1", "Hello client")
        assert msg["content"] == "Hello client"
        assert msg["case_id"] == "c1"

    def test_get_messages(self):
        self.svc.send_message("c1", "a1", "First")
        self.svc.send_message("c1", "u1", "Reply")
        msgs = self.svc.get_messages("c1")
        assert len(msgs) == 2

    def test_generate_status_update(self):
        update = self.svc.generate_status_update("c1")
        assert "Status Update" in update


class TestDocumentScanning:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_scan_passport(self):
        result = self.svc.scan_passport()
        assert result["scan_type"] == "passport"
        assert "CHEN" in result["extracted_data"]["full_name"]
        assert result["confidence_score"] > 0.9

    def test_scan_uscis_notice(self):
        result = self.svc.scan_uscis_notice()
        assert "receipt_number" in result["extracted_data"]

    def test_scan_i94(self):
        result = self.svc.scan_i94()
        assert "admission_number" in result["extracted_data"]


class TestReports:
    def setup_method(self):
        self.svc = AttorneyService()

    def test_caseload_report(self):
        r = self.svc.generate_caseload_report("a1")
        assert r["type"] == "caseload"
        assert "by_visa_type" in r["data"]

    def test_revenue_report(self):
        r = self.svc.generate_revenue_report("a1")
        assert r["data"]["total_revenue_ytd"] > 0

    def test_success_report(self):
        r = self.svc.generate_success_report("a1")
        assert r["data"]["overall_approval_rate"] > 0


# ── Government Portal Service ──

class TestGovernmentService:
    def setup_method(self):
        self.svc = GovernmentPortalService()

    def test_uscis_status(self):
        s = self.svc.check_uscis_status("WAC-26-123-45678")
        assert s["receipt_number"] == "WAC-26-123-45678"
        assert "status" in s

    def test_processing_times(self):
        t = self.svc.get_processing_times("I-129")
        assert "regular" in t
        assert "premium" in t

    def test_visa_bulletin(self):
        vb = self.svc.get_visa_bulletin()
        assert "employment_based" in vb
        assert "EB-1" in vb["employment_based"]

    def test_sevis(self):
        s = self.svc.check_sevis_status("N0012345678")
        assert s["status"] == "Active"

    def test_dol(self):
        s = self.svc.check_dol_status("A-19145-12345")
        assert s["case_type"] == "PERM"

    def test_uk_status(self):
        s = self.svc.check_uk_status("GWF012345678")
        assert "Skilled Worker" in s["application_type"]

    def test_ircc_status(self):
        s = self.svc.check_ircc_status("E001234567")
        assert "Express Entry" in s["application_type"]

    def test_vevo_status(self):
        s = self.svc.check_vevo_status("1234567890")
        assert s["status"] == "In Effect"

    def test_policy_alerts(self):
        alerts = self.svc.get_policy_alerts()
        assert len(alerts) >= 4

    def test_filing_fees(self):
        fees = self.svc.get_filing_fees("I-129")
        assert fees["base_fee"] == 460

    def test_all_statuses(self):
        result = self.svc.get_all_statuses("a1")
        assert "uscis" in result
        assert "dol" in result
        assert "uk" in result


# ── Marketplace Service ──

class TestMarketplace:
    def setup_method(self):
        self.svc = MarketplaceService()

    def test_create_listing(self):
        l = self.svc.create_case_listing({"visa_type": "H-1B", "country": "US"})
        assert l["status"] == "available"

    def test_browse_and_accept(self):
        l = self.svc.create_case_listing({"visa_type": "H-1B"})
        cases = self.svc.browse_cases("a1")
        assert len(cases) == 1
        accepted = self.svc.accept_case("a1", l["id"])
        assert accepted["status"] == "accepted"

    def test_escrow_lifecycle(self):
        esc = self.svc.create_escrow("c1", "app1", "atty1", 5000, [
            {"name": "Intake", "pct": 30},
            {"name": "Filing", "pct": 70},
        ])
        assert esc["total_amount"] == 5000
        assert len(esc["milestones"]) == 2
        m_id = esc["milestones"][0]["id"]
        released = self.svc.release_milestone(esc["id"], m_id, "Signed retainer")
        assert released["milestones"][0]["status"] == "released"

    def test_reviews(self):
        r = self.svc.submit_review("app1", "atty1", "c1", 5, "Excellent service")
        assert r["rating"] == 5
        reviews = self.svc.get_reviews("atty1")
        assert len(reviews) == 1

    def test_dispute(self):
        d = self.svc.initiate_dispute("c1", "app1", "No response")
        assert d["status"] == "open"

    def test_bar_verification(self):
        v = self.svc.verify_bar_number("CA", "123456")
        assert v["verified"] is True

    def test_milestone_definitions(self):
        ms = self.svc.get_milestone_definitions("H-1B")
        assert len(ms) == 4
        assert sum(m["pct"] for m in ms) == 100


# ── AI Engine ──

class TestAIEngine:
    def setup_method(self):
        self.svc = AIEngineService()

    def test_analyze_document(self):
        r = self.svc.analyze_document(document_type="passport")
        assert r["confidence"] > 0.9

    def test_quality_check(self):
        r = self.svc.check_document_quality()
        assert r["acceptable"] is True

    def test_application_scoring(self):
        r = self.svc.score_application_strength({"visa_type": "H-1B"})
        assert 0 <= r["score"] <= 100
        assert len(r["strengths"]) > 0

    def test_attorney_matching(self):
        matches = self.svc.match_attorneys({"visa_type": "H-1B", "country": "US"})
        assert len(matches) >= 3
        assert matches[0]["match_score"] >= matches[1]["match_score"]

    def test_outcome_prediction(self):
        r = self.svc.predict_case_outcome({"visa_type": "H-1B"})
        assert 0 <= r["approval_probability"] <= 1

    def test_cover_letter(self):
        letter = self.svc.generate_cover_letter({"client_name": "Test", "visa_type": "H-1B", "employer": "Acme"})
        assert "H-1B" in letter
        assert "Test" in letter

    def test_translation(self):
        r = self.svc.translate_message("Hello", "en", "zh")
        assert r["disclaimer"]
        assert "Chinese" in r["translated"]

    def test_visa_timeline(self):
        r = self.svc.calculate_visa_timeline("H-1B")
        assert "estimated_decision_date" in r

    def test_cost_calculation(self):
        r = self.svc.calculate_total_cost("H-1B")
        assert r["filing_fees"] > 0
        assert "disclaimer" in r

    def test_pathway_recommendation(self):
        paths = self.svc.recommend_visa_pathway({})
        assert len(paths) >= 3
        assert paths[0]["fit_score"] > paths[1]["fit_score"]


# ── E-Verify ──

class TestEVerify:
    def setup_method(self):
        self.svc = EVerifyService()

    def test_create_case(self):
        c = self.svc.create_case({"name": "John Doe"})
        assert c["result"] == "Employment Authorized"

    def test_bulk_verify(self):
        results = self.svc.bulk_verify([{"name": "A"}, {"name": "B"}, {"name": "C"}])
        assert len(results) == 3

    def test_stats(self):
        self.svc.create_case({"name": "Test"})
        stats = self.svc.get_stats("emp1")
        assert stats["total_cases"] == 1

    def test_i9_section2(self):
        r = self.svc.generate_i9_section2({"name": "Test", "document_title": "US Passport"})
        assert r["remote_verification"] is True

    def test_bulk_i9(self):
        results = self.svc.bulk_process_i9([{"name": "A"}, {"name": "B"}])
        assert len(results) == 2


# ── Integration ──

class TestIntegration:
    def setup_method(self):
        self.svc = IntegrationService()

    def test_csv_roundtrip(self):
        data = [{"name": "Alice", "visa": "H-1B"}, {"name": "Bob", "visa": "L-1"}]
        csv_str = self.svc.export_csv(data, ["name", "visa"])
        imported = self.svc.import_csv(csv_str)
        assert len(imported) == 2
        assert imported[0]["name"] == "Alice"

    def test_api_key(self):
        key = self.svc.get_api_key("u1")
        assert key["api_key"].startswith("vrm_live_")

    def test_webhook(self):
        wh = self.svc.create_zapier_webhook("case_created", "https://hooks.zapier.com/test")
        assert wh["status"] == "active"
        triggered = self.svc.trigger_webhook("case_created", {"case_id": "123"})
        assert len(triggered) == 1

    def test_esignature(self):
        req = self.svc.create_esignature_request("doc1", [{"email": "test@test.com"}])
        assert req["status"] == "pending"
        assert "signing_url" in req

    def test_word_document(self):
        doc = self.svc.generate_word_document("cover_letter", {"client_name": "Test", "visa_type": "H-1B"})
        assert b"H-1B" in doc


# ── Market Intel ──

class TestMarketIntel:
    def setup_method(self):
        self.svc = MarketIntelService()

    def test_competitor_comparison(self):
        comp = self.svc.get_competitor_comparison()
        assert "Envoy Global" in comp["competitors"]
        assert len(comp["competitors"]) >= 6

    def test_market_trends(self):
        trends = self.svc.get_market_trends()
        assert len(trends) >= 5

    def test_immigration_news(self):
        news = self.svc.get_immigration_news()
        assert len(news) >= 4
        us_news = self.svc.get_immigration_news(["US"])
        assert all(n["country"] == "US" for n in us_news)

    def test_feature_suggestions(self):
        features = self.svc.suggest_new_features()
        assert len(features) >= 4

    def test_engagement(self):
        e = self.svc.get_user_engagement("u1")
        assert e["engagement_score"] > 0

    def test_retention(self):
        r = self.svc.get_retention_insights()
        assert r["overall_retention_30d"] > 0
        assert len(r["stickiest_features"]) >= 5
