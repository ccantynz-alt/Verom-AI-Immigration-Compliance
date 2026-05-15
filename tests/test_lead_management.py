"""Tests for the CRM / Lead Management service."""

from immigration_compliance.services.lead_management_service import (
    LeadManagementService,
    PIPELINE_STAGES,
    LEAD_SOURCES,
    VISA_VIABILITY,
)
from immigration_compliance.services.conflict_check_service import ConflictCheckService


def test_pipeline_stages_constant():
    assert "inquiry" in PIPELINE_STAGES
    assert "retained" in PIPELINE_STAGES
    assert "active_case" in PIPELINE_STAGES


def test_lead_sources_include_modern_channels():
    assert "whatsapp" in LEAD_SOURCES
    assert "facebook_messenger" in LEAD_SOURCES
    assert "website_form" in LEAD_SOURCES


def test_capture_lead_initializes_all_fields():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="Wei Chen", email="w@x.com",
                            source="website_form", visa_type="H-1B")
    assert lead["full_name"] == "Wei Chen"
    assert lead["stage"] == "inquiry"
    assert lead["score"] >= 0
    assert "captured_at" in lead


def test_capture_lead_unknown_source_rejected():
    svc = LeadManagementService()
    try:
        svc.capture_lead(firm_id="f1", full_name="X", source="snail_mail")
        assert False
    except ValueError:
        pass


def test_capture_lead_unknown_urgency_rejected():
    svc = LeadManagementService()
    try:
        svc.capture_lead(firm_id="f1", full_name="X", urgency="catastrophic")
        assert False
    except ValueError:
        pass


def test_score_higher_for_known_visa_type():
    svc = LeadManagementService()
    known = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    unknown = svc.capture_lead(firm_id="f1", full_name="B")
    assert known["score"] > unknown["score"]


def test_employer_paying_increases_score():
    svc = LeadManagementService()
    paying = svc.capture_lead(firm_id="f1", full_name="A", visa_type="O-1", employer_paying=True)
    not_paying = svc.capture_lead(firm_id="f1", full_name="B", visa_type="O-1", employer_paying=False)
    assert paying["score_breakdown"]["fee_potential"] > not_paying["score_breakdown"]["fee_potential"]


def test_referral_source_increases_score():
    svc = LeadManagementService()
    referral = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B",
                                source="referral", referrer_name="Dr. Park")
    cold = svc.capture_lead(firm_id="f1", full_name="B", visa_type="H-1B", source="other")
    assert referral["score_breakdown"]["referral_quality"] > cold["score_breakdown"]["referral_quality"]


def test_high_urgency_increases_score():
    svc = LeadManagementService()
    urgent = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B", urgency="immediate")
    chill = svc.capture_lead(firm_id="f1", full_name="B", visa_type="H-1B", urgency="low")
    assert urgent["score_breakdown"]["urgency"] > chill["score_breakdown"]["urgency"]


def test_score_tiers():
    svc = LeadManagementService()
    hot_lead = svc.capture_lead(firm_id="f1", full_name="A", email="a@x.com", phone="1",
                                visa_type="H-1B", source="referral", referrer_name="Dr.",
                                urgency="immediate", employer_paying=True)
    cold_lead = svc.capture_lead(firm_id="f1", full_name="B", source="other")
    # Tier should reflect score
    assert hot_lead["tier"] in ("hot", "warm", "qualified")
    assert cold_lead["tier"] in ("cold", "qualified")


def test_stage_transitions():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    svc.transition_stage(lead["id"], "contacted", reason="initial outreach")
    svc.transition_stage(lead["id"], "consultation_scheduled", reason="booked tuesday")
    refreshed = svc.get_lead(lead["id"])
    assert refreshed["stage"] == "consultation_scheduled"
    assert refreshed["consultation_at"] is not None
    assert len(refreshed["stage_history"]) == 3


def test_invalid_stage_rejected():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    try:
        svc.transition_stage(lead["id"], "invalid_stage")
        assert False
    except ValueError:
        pass


def test_retain_records_timestamp():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    svc.transition_stage(lead["id"], "retained", reason="signed")
    refreshed = svc.get_lead(lead["id"])
    assert refreshed["retained_at"] is not None


def test_lost_records_reason():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    svc.transition_stage(lead["id"], "lost", reason="went elsewhere")
    refreshed = svc.get_lead(lead["id"])
    assert refreshed["lost_reason"] == "went elsewhere"


def test_link_workspace_advances_to_active_case():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    svc.link_to_workspace(lead["id"], "ws-123")
    refreshed = svc.get_lead(lead["id"])
    assert refreshed["linked_workspace_id"] == "ws-123"
    assert refreshed["stage"] == "active_case"


def test_touchpoints_recorded():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    svc.add_touchpoint(lead["id"], channel="phone", direction="outbound", summary="Called")
    svc.add_touchpoint(lead["id"], channel="email", direction="outbound", summary="Sent intro")
    refreshed = svc.get_lead(lead["id"])
    assert refreshed["touchpoint_count"] == 2
    assert refreshed["first_response_at"] is not None
    tps = svc.list_touchpoints(lead_id=lead["id"])
    assert len(tps) == 2


def test_invalid_touchpoint_direction_rejected():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    try:
        svc.add_touchpoint(lead["id"], channel="email", direction="sideways")
        assert False
    except ValueError:
        pass


def test_pipeline_summary_buckets():
    svc = LeadManagementService()
    for i in range(3):
        svc.capture_lead(firm_id="f1", full_name=f"L{i}", visa_type="H-1B")
    l = svc.capture_lead(firm_id="f1", full_name="Retained", visa_type="H-1B")
    svc.transition_stage(l["id"], "retained")
    summary = svc.pipeline_summary(firm_id="f1")
    assert summary["total_leads"] == 4
    assert summary["funnel_counts"]["retained"] == 1


def test_source_attribution_aggregates():
    svc = LeadManagementService()
    svc.capture_lead(firm_id="f1", full_name="A", source="referral", visa_type="H-1B")
    svc.capture_lead(firm_id="f1", full_name="B", source="referral", visa_type="H-1B")
    svc.capture_lead(firm_id="f1", full_name="C", source="website_form", visa_type="H-1B")
    attr = svc.source_attribution(firm_id="f1")
    assert attr["by_source"]["referral"]["count"] == 2
    assert attr["by_source"]["website_form"]["count"] == 1


def test_referral_source_registration():
    svc = LeadManagementService()
    r = svc.register_referral_source("f1", "Dr. Park", contact_email="park@x.com", relationship="academic")
    assert r["name"] == "Dr. Park"
    refs = svc.list_referral_sources(firm_id="f1")
    assert len(refs) == 1


def test_conflict_check_integration_lowers_score():
    cc = ConflictCheckService()
    cc.register_case({"id": "c1", "attorney_id": "atty-1", "firm_id": "f1", "applicant_name": "Jane Doe"})
    svc = LeadManagementService(conflict_check=cc)
    # Jane Doe is already represented by atty-1 → DIRECT_DUPLICATE conflict
    lead = svc.capture_lead(firm_id="f1", full_name="Jane Doe", attorney_id="atty-1", visa_type="H-1B")
    assert lead["score_breakdown"]["conflict_free"] == 0


def test_filter_by_min_score():
    svc = LeadManagementService()
    svc.capture_lead(firm_id="f1", full_name="High", visa_type="H-1B", source="referral",
                     referrer_name="Dr.", urgency="immediate", employer_paying=True,
                     email="h@x.com", phone="1")
    svc.capture_lead(firm_id="f1", full_name="Low", source="other")
    high_only = svc.list_leads(firm_id="f1", min_score=60)
    assert all(l["score"] >= 60 for l in high_only)


def test_visa_viability_constants_present():
    assert "H-1B" in VISA_VIABILITY
    assert "asylum" in VISA_VIABILITY


def test_rescore_after_touchpoints():
    svc = LeadManagementService()
    lead = svc.capture_lead(firm_id="f1", full_name="A", visa_type="H-1B")
    initial_score = lead["score"]
    svc.add_touchpoint(lead["id"], "phone", "outbound", summary="Engaged")
    svc.add_touchpoint(lead["id"], "email", "outbound", summary="Followed up")
    svc.rescore_lead(lead["id"])
    refreshed = svc.get_lead(lead["id"])
    # Engagement should boost
    assert refreshed["score"] >= initial_score
