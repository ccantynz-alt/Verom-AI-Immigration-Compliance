"""Pre-Screened Lead Marketplace — outcome-based attorney economics.

When an applicant completes intake, package the case strength, RFE risk, and
document readiness into a one-page pre-screened brief. Route to attorneys who
match (specialization, country, language, capacity, RFE handling) and let them
choose to accept the case at a transparent fee.

Strategic value:
  - Outcome-based marketplace: attorneys pay per qualified case, not per click
  - First-mover advantage in immigration ("Stripe Connect of immigration leads")
  - Removes the silent-attorney problem at the front: only attorneys who actually
    accept work see leads

Design:
  - Brief is the marketplace unit. Each brief contains the AI summary of a case
    and is offered to up to N matching attorneys.
  - Attorneys can claim, decline, or pass. Claim creates an exclusive engagement.
  - Pricing tiers per case complexity (simple / standard / complex).
  - Platform fee is transparent and disclosed to both sides before claim.
  - Money-back protection window: applicants can revoke within X days if no
    substantive work performed.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from typing import Any


BRIEF_STATUSES = (
    "draft",                # being prepared
    "open",                 # offered to attorneys
    "claimed",              # an attorney accepted
    "engaged",              # client signed retainer
    "completed",            # case closed
    "expired",              # no attorney claimed in window
    "withdrawn",            # applicant revoked
    "revoked",              # platform took down (fraud, etc.)
)

COMPLEXITY_TIERS = ("simple", "standard", "complex", "high_complexity")

# Per-tier platform fee (% of attorney fee charged to applicant).
# Disclosed transparently before claim.
PLATFORM_FEE_BPS: dict[str, int] = {
    "simple": 800,             # 8%
    "standard": 1000,          # 10%
    "complex": 1200,           # 12%
    "high_complexity": 1500,   # 15%
}

# Default revoke window in days
DEFAULT_REVOKE_WINDOW_DAYS = 7


class LeadMarketplaceService:
    """Pre-screened brief marketplace tying intake to attorney matching."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
        attorney_match_service: Any | None = None,
        notification_service: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._match = attorney_match_service
        self._notifications = notification_service
        self._briefs: dict[str, dict] = {}
        self._claims: dict[str, dict] = {}
        self._engagements: dict[str, dict] = {}

    # ---------- brief preparation ----------
    def prepare_brief(
        self,
        applicant_id: str,
        intake_session_id: str,
        applicant_languages: list[str] | None = None,
        offer_to_top_n_attorneys: int = 5,
        attorney_response_window_hours: int = 48,
        revoke_window_days: int = DEFAULT_REVOKE_WINDOW_DAYS,
        complexity_override: str | None = None,
    ) -> dict:
        """Build a pre-screened brief from a completed intake session."""
        if not self._intake:
            raise RuntimeError("Intake engine not wired")
        intake_session = self._intake.get_session(intake_session_id)
        if intake_session is None:
            raise ValueError("Intake session not found")
        if intake_session["applicant_id"] != applicant_id:
            raise ValueError("Intake session does not belong to applicant")

        summary = self._intake.get_intake_summary(intake_session_id)
        visa_type = intake_session["visa_type"]
        country = intake_session["country"]
        strength_score = (summary.get("strength") or {}).get("score", 0)
        flags = summary.get("red_flags") or []
        red_flag_codes = [f.get("code") for f in flags if f.get("code")]

        complexity = complexity_override or self._derive_complexity(visa_type, strength_score, flags)

        # Run attorney match
        candidates: list[dict] = []
        if self._match:
            try:
                m = self._match.match(
                    visa_type=visa_type, country=country,
                    applicant_languages=applicant_languages or ["English"],
                    red_flag_codes=red_flag_codes,
                    limit=offer_to_top_n_attorneys,
                )
                candidates = m.get("results", [])
            except Exception:
                candidates = []

        offered_to = [c.get("attorney_id") for c in candidates if c.get("attorney_id")]

        brief_id = str(uuid.uuid4())
        platform_fee_bps = PLATFORM_FEE_BPS.get(complexity, 1000)
        brief = {
            "id": brief_id,
            "applicant_id": applicant_id,
            "intake_session_id": intake_session_id,
            "visa_type": visa_type, "country": country,
            "strength_score": strength_score,
            "strength_tier": (summary.get("strength") or {}).get("tier"),
            "red_flag_count": len(flags),
            "red_flag_codes": red_flag_codes,
            "complexity": complexity,
            "platform_fee_bps": platform_fee_bps,
            "platform_fee_pct": round(platform_fee_bps / 100, 2),
            "offered_to_attorneys": offered_to,
            "offer_response_window_hours": attorney_response_window_hours,
            "offer_expires_at": (datetime.utcnow() + timedelta(hours=attorney_response_window_hours)).isoformat(),
            "revoke_window_days": revoke_window_days,
            "revoke_until": (datetime.utcnow() + timedelta(days=revoke_window_days)).isoformat(),
            "applicant_languages": applicant_languages or ["English"],
            "documents_ready_count": (summary.get("documents") or {}).get("total_complete"),
            "summary_excerpt": self._compose_summary_excerpt(intake_session, summary),
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "claimed_by_attorney_id": None,
            "claimed_at": None,
            "engagement_id": None,
        }
        self._briefs[brief_id] = brief

        # Notify each candidate attorney
        if self._notifications:
            for atty_id in offered_to:
                try:
                    self._notifications.emit(
                        event_type="case.attorney_assigned",
                        recipient_user_id=atty_id,
                        title=f"New {visa_type} brief available",
                        body=(
                            f"Strength {strength_score}/100, "
                            f"{len(flags)} flag(s), complexity={complexity}. "
                            f"Respond within {attorney_response_window_hours}h."
                        ),
                        metadata={"brief_id": brief_id, "visa_type": visa_type, "country": country},
                    )
                except Exception:
                    pass

        return brief

    @staticmethod
    def _derive_complexity(visa_type: str, strength: int, flags: list[dict]) -> str:
        # Visa baseline
        complex_visas = {"O-1", "EB-1A", "EB-1B", "EB-2-NIW", "L-1", "EB-5"}
        baseline = "complex" if visa_type in complex_visas else "standard"
        # Adjust based on flags / strength
        blocking = sum(1 for f in flags if f.get("severity") == "blocking")
        high_severity = sum(1 for f in flags if f.get("severity") == "high")
        if blocking > 0:
            return "high_complexity"
        if high_severity >= 2 or strength < 50:
            return "complex"
        if strength >= 80 and high_severity == 0 and visa_type not in complex_visas:
            return "simple"
        return baseline

    @staticmethod
    def _compose_summary_excerpt(intake_session: dict, summary: dict) -> str:
        s = summary.get("strength") or {}
        ans = intake_session.get("answers") or {}
        bits: list[str] = []
        bits.append(f"{intake_session.get('visa_type')} applicant.")
        if s:
            bits.append(f"Strength: {s.get('tier','?')} ({s.get('score',0)}/100).")
        red_flags = summary.get("red_flags") or []
        if red_flags:
            bits.append(f"{len(red_flags)} red flag(s) including: " + ", ".join(f.get('code', '') for f in red_flags[:2]))
        if ans.get("first_name") and ans.get("last_name"):
            bits.append(f"Beneficiary: {ans['first_name']} {ans['last_name']}.")
        return " ".join(bits)

    # ---------- claiming ----------
    def claim_brief(self, brief_id: str, attorney_id: str, attorney_fee_quoted_usd: float) -> dict:
        brief = self._briefs.get(brief_id)
        if brief is None:
            raise ValueError("Brief not found")
        if brief["status"] != "open":
            raise ValueError(f"Brief is not open (status={brief['status']})")
        if attorney_id not in brief["offered_to_attorneys"]:
            raise ValueError("Attorney was not on the offer list")
        if datetime.fromisoformat(brief["offer_expires_at"]) < datetime.utcnow():
            brief["status"] = "expired"
            raise ValueError("Offer has expired")
        # Record the claim
        claim_id = str(uuid.uuid4())
        platform_fee_amount = round(attorney_fee_quoted_usd * brief["platform_fee_bps"] / 10000, 2)
        record = {
            "id": claim_id,
            "brief_id": brief_id, "attorney_id": attorney_id,
            "attorney_fee_quoted_usd": attorney_fee_quoted_usd,
            "platform_fee_amount_usd": platform_fee_amount,
            "platform_fee_bps": brief["platform_fee_bps"],
            "claimed_at": datetime.utcnow().isoformat(),
            "status": "pending_applicant_acceptance",
        }
        self._claims[claim_id] = record
        brief["status"] = "claimed"
        brief["claimed_by_attorney_id"] = attorney_id
        brief["claimed_at"] = record["claimed_at"]
        # Notify applicant
        if self._notifications:
            try:
                self._notifications.emit(
                    event_type="case.attorney_assigned",
                    recipient_user_id=brief["applicant_id"],
                    title="An attorney has accepted your case",
                    body=(
                        f"Quoted attorney fee: ${attorney_fee_quoted_usd}. "
                        f"Platform fee: ${platform_fee_amount} ({brief['platform_fee_pct']}%). "
                        "Review and accept to engage."
                    ),
                    metadata={"brief_id": brief_id, "claim_id": claim_id},
                )
            except Exception:
                pass
        return record

    def accept_claim(self, claim_id: str, applicant_id: str) -> dict:
        claim = self._claims.get(claim_id)
        if claim is None:
            raise ValueError("Claim not found")
        brief = self._briefs.get(claim["brief_id"])
        if brief is None or brief["applicant_id"] != applicant_id:
            raise ValueError("Access denied")
        if claim["status"] != "pending_applicant_acceptance":
            raise ValueError(f"Claim is not pending acceptance (status={claim['status']})")
        claim["status"] = "accepted"
        claim["accepted_at"] = datetime.utcnow().isoformat()
        engagement_id = str(uuid.uuid4())
        engagement = {
            "id": engagement_id,
            "brief_id": claim["brief_id"],
            "applicant_id": applicant_id,
            "attorney_id": claim["attorney_id"],
            "attorney_fee_usd": claim["attorney_fee_quoted_usd"],
            "platform_fee_usd": claim["platform_fee_amount_usd"],
            "engaged_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self._engagements[engagement_id] = engagement
        brief["status"] = "engaged"
        brief["engagement_id"] = engagement_id
        return engagement

    def decline_brief(self, brief_id: str, attorney_id: str, reason: str = "") -> dict:
        brief = self._briefs.get(brief_id)
        if brief is None:
            raise ValueError("Brief not found")
        # Just remove the attorney from the offer list — don't change brief status
        # unless this was the last offered attorney
        if attorney_id in brief["offered_to_attorneys"]:
            brief["offered_to_attorneys"].remove(attorney_id)
        if not brief["offered_to_attorneys"] and brief["status"] == "open":
            brief["status"] = "expired"
        return brief

    def withdraw_brief(self, brief_id: str, applicant_id: str, reason: str = "") -> dict:
        brief = self._briefs.get(brief_id)
        if brief is None:
            raise ValueError("Brief not found")
        if brief["applicant_id"] != applicant_id:
            raise ValueError("Access denied")
        # If engaged, only allow during revoke window
        if brief["status"] == "engaged":
            revoke_until = datetime.fromisoformat(brief["revoke_until"])
            if datetime.utcnow() > revoke_until:
                raise ValueError("Revoke window expired — contact support for refund options")
        brief["status"] = "withdrawn"
        brief["withdrawn_at"] = datetime.utcnow().isoformat()
        brief["withdrawal_reason"] = reason
        return brief

    # ---------- queries ----------
    def get_brief(self, brief_id: str) -> dict | None:
        return self._briefs.get(brief_id)

    def list_briefs(
        self,
        applicant_id: str | None = None,
        attorney_id: str | None = None,
        status: str | None = None,
        offered_to_attorney_id: str | None = None,
    ) -> list[dict]:
        out = list(self._briefs.values())
        if applicant_id:
            out = [b for b in out if b["applicant_id"] == applicant_id]
        if attorney_id:
            out = [b for b in out if b.get("claimed_by_attorney_id") == attorney_id]
        if offered_to_attorney_id:
            out = [b for b in out if offered_to_attorney_id in b["offered_to_attorneys"]]
        if status:
            out = [b for b in out if b["status"] == status]
        return sorted(out, key=lambda b: b["created_at"], reverse=True)

    def list_claims(self, attorney_id: str | None = None, brief_id: str | None = None) -> list[dict]:
        out = list(self._claims.values())
        if attorney_id:
            out = [c for c in out if c["attorney_id"] == attorney_id]
        if brief_id:
            out = [c for c in out if c["brief_id"] == brief_id]
        return out

    def list_engagements(
        self, applicant_id: str | None = None, attorney_id: str | None = None,
    ) -> list[dict]:
        out = list(self._engagements.values())
        if applicant_id:
            out = [e for e in out if e["applicant_id"] == applicant_id]
        if attorney_id:
            out = [e for e in out if e["attorney_id"] == attorney_id]
        return out

    # ---------- introspection ----------
    @staticmethod
    def list_complexity_tiers() -> list[dict]:
        return [
            {"tier": t, "platform_fee_pct": PLATFORM_FEE_BPS.get(t, 1000) / 100}
            for t in COMPLEXITY_TIERS
        ]

    @staticmethod
    def list_brief_statuses() -> list[str]:
        return list(BRIEF_STATUSES)
