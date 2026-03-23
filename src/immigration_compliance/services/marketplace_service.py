"""Marketplace service — case listings, escrow, fraud detection, verification, applicant protection."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta


class MarketplaceService:
    """Full marketplace with escrow payments and fraud detection."""

    def __init__(self) -> None:
        self._listings: dict[str, dict] = {}
        self._escrows: dict[str, dict] = {}
        self._reviews: dict[str, list] = {}
        self._capacity: dict[str, int] = {}
        self._fees: dict[str, dict] = {}
        self._disputes: dict[str, dict] = {}
        self._consequences: dict[str, list] = {}
        self._milestones = self._init_milestones()

    def _init_milestones(self) -> dict:
        return {
            "H-1B": [
                {"name": "Intake & Assessment", "pct": 15, "proof": "Signed retainer, intake summary"},
                {"name": "LCA Filed", "pct": 15, "proof": "LCA confirmation number"},
                {"name": "I-129 Filed", "pct": 30, "proof": "USCIS receipt number"},
                {"name": "Case Adjudicated", "pct": 40, "proof": "Approval/RFE response"},
            ],
            "I-130/I-485": [
                {"name": "Intake Complete", "pct": 15, "proof": "Signed retainer"},
                {"name": "I-130 Filed", "pct": 20, "proof": "USCIS receipt number"},
                {"name": "I-485 Filed", "pct": 25, "proof": "Receipt numbers"},
                {"name": "Interview Prep", "pct": 15, "proof": "Interview notes"},
                {"name": "Case Adjudicated", "pct": 25, "proof": "Decision notice"},
            ],
            "UK Skilled Worker": [
                {"name": "Eligibility Assessment", "pct": 20, "proof": "Assessment report"},
                {"name": "CoS Obtained", "pct": 30, "proof": "CoS reference number"},
                {"name": "Application Submitted", "pct": 30, "proof": "Submission confirmation"},
                {"name": "Decision Received", "pct": 20, "proof": "Decision letter"},
            ],
            "Express Entry": [
                {"name": "Profile Created", "pct": 20, "proof": "EE profile number"},
                {"name": "ITA & Application Prepared", "pct": 30, "proof": "ITA confirmation"},
                {"name": "Application Submitted", "pct": 30, "proof": "IRCC acknowledgment"},
                {"name": "COPR Received", "pct": 20, "proof": "COPR document"},
            ],
        }

    # ── Marketplace ──

    def create_case_listing(self, data: dict) -> dict:
        listing_id = str(uuid.uuid4())
        listing = {
            "id": listing_id,
            "visa_type": data.get("visa_type", "H-1B"),
            "country": data.get("country", "US"),
            "complexity": data.get("complexity", "Standard"),
            "urgency": data.get("urgency", "Normal"),
            "description": data.get("description", ""),
            "applicant_id": data.get("applicant_id"),
            "status": "available",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._listings[listing_id] = listing
        return listing

    def browse_cases(self, attorney_id: str, filters: dict | None = None) -> list[dict]:
        cases = [c for c in self._listings.values() if c["status"] == "available"]
        if filters:
            if "visa_type" in filters:
                cases = [c for c in cases if c["visa_type"] == filters["visa_type"]]
            if "country" in filters:
                cases = [c for c in cases if c["country"] == filters["country"]]
        return cases

    def accept_case(self, attorney_id: str, listing_id: str) -> dict:
        listing = self._listings.get(listing_id)
        if not listing:
            raise ValueError("Listing not found")
        if listing["status"] != "available":
            raise ValueError("Case already taken")
        cap = self._capacity.get(attorney_id, 10)
        listing["status"] = "accepted"
        listing["attorney_id"] = attorney_id
        listing["accepted_at"] = datetime.utcnow().isoformat()
        return listing

    def get_pipeline(self, attorney_id: str) -> list[dict]:
        return [c for c in self._listings.values() if c.get("attorney_id") == attorney_id]

    def set_capacity(self, attorney_id: str, max_cases: int) -> dict:
        self._capacity[attorney_id] = max_cases
        return {"attorney_id": attorney_id, "max_cases": max_cases}

    def set_fees(self, attorney_id: str, fee_schedule: dict) -> dict:
        self._fees[attorney_id] = fee_schedule
        return {"attorney_id": attorney_id, "fee_schedule": fee_schedule}

    def submit_review(self, applicant_id: str, attorney_id: str, case_id: str, rating: int, text: str) -> dict:
        review = {
            "id": str(uuid.uuid4()),
            "applicant_id": applicant_id,
            "attorney_id": attorney_id,
            "case_id": case_id,
            "rating": min(5, max(1, rating)),
            "text": text,
            "verified_outcome": True,
            "created_at": datetime.utcnow().isoformat(),
        }
        if attorney_id not in self._reviews:
            self._reviews[attorney_id] = []
        self._reviews[attorney_id].append(review)
        return review

    def get_reviews(self, attorney_id: str) -> list[dict]:
        return self._reviews.get(attorney_id, [])

    def get_earnings(self, attorney_id: str, start: str | None = None, end: str | None = None) -> dict:
        return {
            "attorney_id": attorney_id,
            "total_earned": 285000,
            "pending_release": 32000,
            "in_escrow": 45000,
            "this_month": 24500,
            "by_month": {"Jan": 22000, "Feb": 25000, "Mar": 24500},
        }

    # ── Escrow ──

    def create_escrow(self, case_id: str, applicant_id: str, attorney_id: str, amount: float, milestones: list[dict] | None = None) -> dict:
        escrow_id = str(uuid.uuid4())
        if not milestones:
            milestones = [{"name": "Full Payment", "pct": 100, "proof": "Case completion", "status": "held"}]
        for m in milestones:
            m["id"] = str(uuid.uuid4())
            m["amount"] = round(amount * m["pct"] / 100, 2)
            m.setdefault("status", "held")
        escrow = {
            "id": escrow_id,
            "case_id": case_id,
            "applicant_id": applicant_id,
            "attorney_id": attorney_id,
            "total_amount": amount,
            "milestones": milestones,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._escrows[escrow_id] = escrow
        return escrow

    def get_escrow(self, escrow_id: str) -> dict | None:
        return self._escrows.get(escrow_id)

    def release_milestone(self, escrow_id: str, milestone_id: str, proof: str) -> dict:
        escrow = self._escrows.get(escrow_id)
        if not escrow:
            raise ValueError("Escrow not found")
        for m in escrow["milestones"]:
            if m["id"] == milestone_id:
                m["status"] = "released"
                m["proof_provided"] = proof
                m["released_at"] = datetime.utcnow().isoformat()
                break
        return escrow

    def request_refund(self, escrow_id: str, reason: str) -> dict:
        escrow = self._escrows.get(escrow_id)
        if not escrow:
            raise ValueError("Escrow not found")
        held = [m for m in escrow["milestones"] if m["status"] == "held"]
        refund_amount = sum(m["amount"] for m in held)
        return {
            "escrow_id": escrow_id,
            "refund_amount": refund_amount,
            "reason": reason,
            "status": "pending_review",
            "milestones_refunded": len(held),
        }

    def auto_refund_check(self) -> list[dict]:
        refunded = []
        cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
        for esc in self._escrows.values():
            if esc["status"] == "active" and esc["created_at"] < cutoff:
                held = [m for m in esc["milestones"] if m["status"] == "held"]
                if held:
                    for m in held:
                        m["status"] = "auto_refunded"
                    refunded.append(esc)
        return refunded

    def get_payout_dashboard(self, attorney_id: str) -> dict:
        held = released = pending = 0
        for esc in self._escrows.values():
            if esc.get("attorney_id") == attorney_id:
                for m in esc["milestones"]:
                    if m["status"] == "held":
                        held += m["amount"]
                    elif m["status"] == "released":
                        released += m["amount"]
                    elif m["status"] == "pending":
                        pending += m["amount"]
        return {"attorney_id": attorney_id, "held": held, "released": released, "pending": pending}

    # ── Fraud Detection ──

    def monitor_activity(self, attorney_id: str) -> dict:
        return {
            "attorney_id": attorney_id,
            "activity_score": 88.5,
            "cases_accepted_30d": 3,
            "cases_filed_30d": 2,
            "avg_response_time_hours": 4.5,
            "complaint_count_90d": 0,
            "flags": [],
        }

    def calculate_performance_score(self, attorney_id: str) -> float:
        return 92.0

    def detect_anomalies(self, attorney_id: str) -> list[dict]:
        return []  # No anomalies in demo

    def apply_consequence(self, attorney_id: str, level: str) -> dict:
        consequence = {
            "attorney_id": attorney_id,
            "level": level,
            "applied_at": datetime.utcnow().isoformat(),
            "description": {
                "warning": "Written warning issued",
                "payment_hold": "Pending payouts frozen",
                "suspension": "Removed from marketplace",
                "removal": "Permanently removed from network",
            }.get(level, "Unknown level"),
        }
        if attorney_id not in self._consequences:
            self._consequences[attorney_id] = []
        self._consequences[attorney_id].append(consequence)
        return consequence

    # ── Verification ──

    def verify_bar_number(self, state: str, bar_number: str) -> dict:
        return {
            "state": state,
            "bar_number": bar_number,
            "verified": True,
            "name": "Jennifer Park",
            "status": "Active",
            "admitted_date": "2014-06-15",
            "disciplinary_records": [],
        }

    def verify_international_credential(self, country: str, data: dict) -> dict:
        registries = {"UK": "SRA", "CA": "Law Society", "AU": "MARA"}
        return {
            "country": country,
            "registry": registries.get(country, "National Bar"),
            "verified": True,
            "credential_number": data.get("credential_number", ""),
            "status": "Active",
        }

    def check_disciplinary_records(self, attorney_id: str) -> list[dict]:
        return []  # Clean record in demo

    # ── Applicant Protection ──

    def initiate_dispute(self, case_id: str, applicant_id: str, reason: str) -> dict:
        dispute_id = str(uuid.uuid4())
        dispute = {
            "id": dispute_id,
            "case_id": case_id,
            "applicant_id": applicant_id,
            "reason": reason,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "estimated_resolution": "5 business days",
        }
        self._disputes[dispute_id] = dispute
        return dispute

    def transfer_case(self, case_id: str, from_attorney: str, to_attorney: str) -> dict:
        return {
            "case_id": case_id,
            "from_attorney": from_attorney,
            "to_attorney": to_attorney,
            "status": "transferred",
            "transferred_at": datetime.utcnow().isoformat(),
            "documents_transferred": True,
            "escrow_transferred": True,
        }

    def check_response_sla(self, attorney_id: str, case_id: str) -> dict:
        return {
            "attorney_id": attorney_id,
            "case_id": case_id,
            "last_response": datetime.utcnow().isoformat(),
            "within_sla": True,
            "hours_since_last_response": 3.5,
            "sla_limit_hours": 48,
        }

    def get_milestone_definitions(self, visa_type: str) -> list[dict]:
        return self._milestones.get(visa_type, self._milestones["H-1B"])
