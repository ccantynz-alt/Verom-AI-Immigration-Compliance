"""CRM / Lead Management service.

Built specifically for immigration practice — captures inbound leads
from website forms, WhatsApp, Facebook Messenger, SMS, and phone, scores
them by case viability and complexity, and tracks the conversion pipeline
from inquiry → consultation → retained → active case.

The piece that combines CRM with case management — no competitor combines
both well.

Concepts:
  - Lead              prospect at any pipeline stage
  - LeadSource        capture channel (website / whatsapp / referral / etc.)
  - PipelineStage     inquiry / contacted / consultation_scheduled /
                      consulted / proposal_sent / retained / declined / lost
  - LeadScore         composite of viability, complexity, and fee potential
  - Touchpoint        every contact event (call, email, sms, message)
  - ConversionEvent   stage transition with timestamp + reason
  - Referral          referring person/firm with attribution

Lead scoring (rules-based, explainable):
  - Visa type viability (15 pts): clear path vs. tough case
  - Documentation readiness (10 pts): how prepared the inquirer is
  - Engagement signal (15 pts): response speed + touchpoint count
  - Fee potential (15 pts): visa type complexity + employer-paid
  - Urgency (10 pts): processing time pressure
  - Referral quality (10 pts): warm intro vs. cold website lead
  - Geographic fit (5 pts): jurisdiction match
  - Conflict-free flag (10 pts): conflict check passes
  - Communication health (10 pts): consistent + complete responses
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Pipeline catalog
# ---------------------------------------------------------------------------

PIPELINE_STAGES = (
    "inquiry",                   # just came in
    "contacted",                 # firm reached out
    "consultation_scheduled",    # consult on calendar
    "consulted",                 # consult happened
    "proposal_sent",             # fee agreement out
    "retained",                  # signed retainer
    "active_case",               # converted to a case workspace
    "declined",                  # firm declined the case
    "lost",                      # lead went elsewhere
)

LEAD_SOURCES = (
    "website_form", "whatsapp", "facebook_messenger", "sms",
    "phone", "email", "referral", "walkin", "social_media",
    "google_ads", "directory_listing", "other",
)

VISA_VIABILITY: dict[str, int] = {
    "H-1B": 12, "L-1": 13, "O-1": 11, "EB-1A": 9, "EB-1B": 10,
    "EB-2-NIW": 10, "EB-2": 12, "EB-3": 13, "TN": 14, "E-2": 11,
    "E-3": 12, "F-1": 14, "J-1": 14, "I-130": 13, "I-485": 12,
    "K-1": 11, "I-751": 12, "N-400": 14, "removal_defense": 6,
    "asylum": 8, "U_visa": 8, "T_visa": 8, "DACA": 7,
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LeadManagementService:
    """End-to-end CRM for immigration practice."""

    def __init__(self, conflict_check: Any | None = None) -> None:
        self._conflict_check = conflict_check
        self._leads: dict[str, dict] = {}
        self._touchpoints: list[dict] = []
        self._conversion_events: list[dict] = []
        self._referrals: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_pipeline_stages() -> list[str]:
        return list(PIPELINE_STAGES)

    @staticmethod
    def list_lead_sources() -> list[str]:
        return list(LEAD_SOURCES)

    # ---------- lead capture ----------
    def capture_lead(
        self,
        firm_id: str,
        full_name: str,
        email: str = "",
        phone: str = "",
        source: str = "website_form",
        visa_type: str | None = None,
        country_of_birth: str | None = None,
        country_of_destination: str = "US",
        urgency: str = "normal",       # low / normal / high / immediate
        employer_paying: bool = False,
        referrer_name: str = "",
        notes: str = "",
        attorney_id: str | None = None,
        custom_fields: dict | None = None,
    ) -> dict:
        if source not in LEAD_SOURCES:
            raise ValueError(f"Unknown source: {source}")
        if urgency not in ("low", "normal", "high", "immediate"):
            raise ValueError(f"Unknown urgency: {urgency}")
        lead_id = str(uuid.uuid4())
        record = {
            "id": lead_id, "firm_id": firm_id,
            "full_name": full_name, "email": email, "phone": phone,
            "source": source, "visa_type": visa_type,
            "country_of_birth": country_of_birth,
            "country_of_destination": country_of_destination,
            "urgency": urgency, "employer_paying": employer_paying,
            "referrer_name": referrer_name, "notes": notes,
            "attorney_id": attorney_id,
            "custom_fields": custom_fields or {},
            "stage": "inquiry",
            "score": 0,
            "score_breakdown": {},
            "score_reasons": [],
            "captured_at": datetime.utcnow().isoformat(),
            "stage_history": [{"stage": "inquiry", "at": datetime.utcnow().isoformat()}],
            "touchpoint_count": 0,
            "first_response_at": None,
            "consultation_at": None,
            "retained_at": None,
            "lost_reason": None,
            "linked_workspace_id": None,
        }
        self._leads[lead_id] = record
        # Auto-score on capture
        self.rescore_lead(lead_id)
        return record

    def get_lead(self, lead_id: str) -> dict | None:
        return self._leads.get(lead_id)

    def list_leads(
        self, firm_id: str | None = None, stage: str | None = None,
        attorney_id: str | None = None, source: str | None = None,
        min_score: int | None = None,
    ) -> list[dict]:
        out = list(self._leads.values())
        if firm_id:
            out = [l for l in out if l["firm_id"] == firm_id]
        if stage:
            out = [l for l in out if l["stage"] == stage]
        if attorney_id:
            out = [l for l in out if l.get("attorney_id") == attorney_id]
        if source:
            out = [l for l in out if l["source"] == source]
        if min_score is not None:
            out = [l for l in out if l["score"] >= min_score]
        return sorted(out, key=lambda l: -l["score"])

    # ---------- stage transitions ----------
    def transition_stage(
        self, lead_id: str, new_stage: str,
        reason: str = "", actor_id: str | None = None,
    ) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            raise ValueError(f"Lead not found: {lead_id}")
        if new_stage not in PIPELINE_STAGES:
            raise ValueError(f"Unknown stage: {new_stage}")
        old_stage = lead["stage"]
        lead["stage"] = new_stage
        now = datetime.utcnow().isoformat()
        lead["stage_history"].append({"stage": new_stage, "at": now, "reason": reason})
        # Stage-specific timestamps
        if new_stage == "consultation_scheduled" and not lead["consultation_at"]:
            lead["consultation_at"] = now
        if new_stage == "retained":
            lead["retained_at"] = now
        if new_stage == "lost":
            lead["lost_reason"] = reason
        # Conversion event
        self._conversion_events.append({
            "lead_id": lead_id, "from_stage": old_stage, "to_stage": new_stage,
            "reason": reason, "actor_id": actor_id, "at": now,
        })
        return lead

    def link_to_workspace(self, lead_id: str, workspace_id: str) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            raise ValueError(f"Lead not found: {lead_id}")
        lead["linked_workspace_id"] = workspace_id
        if lead["stage"] != "active_case":
            self.transition_stage(lead_id, "active_case", reason="Workspace created")
        return lead

    # ---------- touchpoints ----------
    def add_touchpoint(
        self, lead_id: str, channel: str, direction: str = "outbound",
        summary: str = "", at: str | None = None, actor_id: str | None = None,
    ) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            raise ValueError(f"Lead not found: {lead_id}")
        if direction not in ("inbound", "outbound"):
            raise ValueError("Direction must be 'inbound' or 'outbound'")
        record = {
            "id": str(uuid.uuid4()),
            "lead_id": lead_id,
            "channel": channel, "direction": direction,
            "summary": summary,
            "actor_id": actor_id,
            "at": at or datetime.utcnow().isoformat(),
        }
        self._touchpoints.append(record)
        lead["touchpoint_count"] += 1
        if not lead["first_response_at"] and direction == "outbound":
            lead["first_response_at"] = record["at"]
        return record

    def list_touchpoints(self, lead_id: str | None = None, limit: int = 100) -> list[dict]:
        out = self._touchpoints
        if lead_id:
            out = [t for t in out if t["lead_id"] == lead_id]
        return out[-limit:]

    # ---------- scoring ----------
    def rescore_lead(self, lead_id: str) -> dict:
        lead = self._leads.get(lead_id)
        if lead is None:
            raise ValueError(f"Lead not found: {lead_id}")
        breakdown: dict[str, int] = {}
        reasons: list[str] = []

        # Visa viability (15)
        if lead["visa_type"] and lead["visa_type"] in VISA_VIABILITY:
            v = VISA_VIABILITY[lead["visa_type"]]
            breakdown["visa_viability"] = v
            reasons.append(f"{lead['visa_type']} has clear regulatory pathway")
        else:
            breakdown["visa_viability"] = 5
            reasons.append("Visa type not yet specified — lower confidence")

        # Documentation readiness (10) — derived from custom_fields
        readiness = lead.get("custom_fields", {}).get("documents_ready_count")
        if readiness:
            try:
                count = int(readiness)
                breakdown["documentation_readiness"] = min(10, count * 2)
                reasons.append(f"Inquirer has {count} documents already prepared")
            except (TypeError, ValueError):
                breakdown["documentation_readiness"] = 0
        else:
            breakdown["documentation_readiness"] = 0

        # Engagement (15) — touchpoint count + first-response speed
        tp = lead["touchpoint_count"]
        engagement = min(10, tp * 2)
        if lead["first_response_at"] and lead["captured_at"]:
            try:
                gap = datetime.fromisoformat(lead["first_response_at"]) - datetime.fromisoformat(lead["captured_at"])
                if gap.total_seconds() < 4 * 3600:  # responded within 4 hours
                    engagement += 5
                    reasons.append("First response within 4 hours")
            except ValueError:
                pass
        breakdown["engagement"] = min(15, engagement)

        # Fee potential (15) — visa complexity + employer paying
        complex_visas = {"O-1", "EB-1A", "EB-1B", "EB-2-NIW", "L-1"}
        fee = 8 if lead["visa_type"] in complex_visas else 5
        if lead["employer_paying"]:
            fee += 5
            reasons.append("Employer paying — corporate-rate fee potential")
        breakdown["fee_potential"] = min(15, fee)

        # Urgency (10)
        urgency_score = {"immediate": 10, "high": 8, "normal": 5, "low": 2}
        breakdown["urgency"] = urgency_score.get(lead["urgency"], 5)
        if lead["urgency"] in ("high", "immediate"):
            reasons.append(f"Urgency: {lead['urgency']} — priority handling")

        # Referral quality (10)
        if lead["source"] == "referral" or lead["referrer_name"]:
            breakdown["referral_quality"] = 10
            reasons.append(f"Warm referral{' from ' + lead['referrer_name'] if lead['referrer_name'] else ''}")
        elif lead["source"] in ("website_form", "google_ads"):
            breakdown["referral_quality"] = 5
        else:
            breakdown["referral_quality"] = 3

        # Geographic fit (5) — assume firm operates in destination country
        if lead["country_of_destination"] == "US":
            breakdown["geographic_fit"] = 5
        else:
            breakdown["geographic_fit"] = 2

        # Conflict-free flag (10) — run conflict check if service is wired
        breakdown["conflict_free"] = 10  # default to clear
        if self._conflict_check:
            try:
                cc_result = self._conflict_check.check_new_case(
                    {"applicant_name": lead["full_name"]},
                    attorney_id=lead.get("attorney_id") or "unassigned",
                    firm_id=lead.get("firm_id"),
                )
                if cc_result["decision"] == "decline_unless_waived":
                    breakdown["conflict_free"] = 0
                    reasons.append("Conflict check: BLOCKING")
                elif cc_result["decision"] == "review_required":
                    breakdown["conflict_free"] = 5
                    reasons.append("Conflict check: review required")
                else:
                    reasons.append("Conflict check: clear")
            except Exception:
                pass

        # Communication health (10) — has email or phone, complete name
        comm = 0
        if lead.get("email"):
            comm += 5
        if lead.get("phone"):
            comm += 5
        breakdown["communication"] = min(10, comm)

        total = sum(breakdown.values())
        lead["score"] = total
        lead["score_breakdown"] = breakdown
        lead["score_reasons"] = reasons
        lead["scored_at"] = datetime.utcnow().isoformat()
        lead["tier"] = self._tier(total)
        return lead

    @staticmethod
    def _tier(score: int) -> str:
        if score >= 80: return "hot"
        if score >= 60: return "warm"
        if score >= 40: return "qualified"
        return "cold"

    # ---------- referrals ----------
    def register_referral_source(
        self, firm_id: str, name: str, contact_email: str = "", relationship: str = "",
    ) -> dict:
        ref_id = str(uuid.uuid4())
        record = {
            "id": ref_id, "firm_id": firm_id, "name": name,
            "contact_email": contact_email, "relationship": relationship,
            "registered_at": datetime.utcnow().isoformat(),
            "lead_count": 0, "retained_count": 0,
        }
        self._referrals[ref_id] = record
        return record

    def list_referral_sources(self, firm_id: str | None = None) -> list[dict]:
        out = list(self._referrals.values())
        if firm_id:
            out = [r for r in out if r["firm_id"] == firm_id]
        return out

    # ---------- pipeline analytics ----------
    def pipeline_summary(self, firm_id: str | None = None) -> dict:
        leads = self.list_leads(firm_id=firm_id)
        by_stage = {stage: 0 for stage in PIPELINE_STAGES}
        for l in leads:
            by_stage[l["stage"]] = by_stage.get(l["stage"], 0) + 1
        # Conversion funnel
        funnel_counts = {
            "inquiries": sum(1 for l in leads if l["stage"] != "lost"),
            "consulted": sum(1 for l in leads if l["stage"] in ("consulted", "proposal_sent", "retained", "active_case")),
            "retained": sum(1 for l in leads if l["stage"] in ("retained", "active_case")),
            "active": sum(1 for l in leads if l["stage"] == "active_case"),
            "lost": sum(1 for l in leads if l["stage"] == "lost"),
        }
        # Conversion rates
        n = funnel_counts["inquiries"] or 1
        conversion = {
            "inquiry_to_consult": round((funnel_counts["consulted"] / n) * 100, 1),
            "inquiry_to_retained": round((funnel_counts["retained"] / n) * 100, 1),
            "consult_to_retained": round((funnel_counts["retained"] / max(funnel_counts["consulted"], 1)) * 100, 1),
        }
        # Score distribution
        tiers = {"hot": 0, "warm": 0, "qualified": 0, "cold": 0}
        for l in leads:
            tiers[l.get("tier", "cold")] = tiers.get(l.get("tier", "cold"), 0) + 1
        return {
            "firm_id": firm_id, "total_leads": len(leads),
            "by_stage": by_stage,
            "funnel_counts": funnel_counts,
            "conversion_rates_pct": conversion,
            "score_tiers": tiers,
            "computed_at": datetime.utcnow().isoformat(),
        }

    def source_attribution(self, firm_id: str | None = None) -> dict:
        leads = self.list_leads(firm_id=firm_id)
        by_source: dict[str, dict] = {}
        for l in leads:
            src = l["source"]
            if src not in by_source:
                by_source[src] = {"count": 0, "retained": 0, "avg_score": 0.0}
            by_source[src]["count"] += 1
            if l["stage"] in ("retained", "active_case"):
                by_source[src]["retained"] += 1
        # Compute averages
        for src in by_source:
            src_leads = [l for l in leads if l["source"] == src]
            if src_leads:
                by_source[src]["avg_score"] = round(sum(l["score"] for l in src_leads) / len(src_leads), 1)
            n = by_source[src]["count"] or 1
            by_source[src]["conversion_rate_pct"] = round((by_source[src]["retained"] / n) * 100, 1)
        return {"firm_id": firm_id, "by_source": by_source, "computed_at": datetime.utcnow().isoformat()}
