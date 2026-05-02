"""Approval Index Service — outcome data + the most defensible asset on the platform.

Records every closed case outcome (approved / denied / withdrawn / RFE-then-approved)
across visa type × country × service center × attorney cohort. Computes the Approval
Index quarterly: a real, audited, source-of-truth approval rate by every relevant
slice. After ~2,000 closed cases, this becomes the single most defensible asset on
the platform — no incumbent can reproduce it because they don't have the marketplace
data.

The Index is published with confidence intervals: <50 cases per slice = "insufficient
data"; 50-200 = "preliminary"; 200+ = "audited". Slices below 5 cases never expose
individual case outcomes (privacy + statistical noise).

Composes with:
  - CaseWorkspaceService (closed cases as the data source)
  - LegalResearchService (corpus updates trigger Index recomputation)
  - BenchmarkReportService (Index feeds the annual report)
"""

from __future__ import annotations

import math
import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Outcome categories
# ---------------------------------------------------------------------------

OUTCOMES = (
    "approved",
    "denied",
    "withdrawn",
    "rfe_then_approved",
    "rfe_then_denied",
    "noid_then_approved",
    "noid_then_denied",
    "abandoned",
)

POSITIVE_OUTCOMES = ("approved", "rfe_then_approved", "noid_then_approved")
NEGATIVE_OUTCOMES = ("denied", "rfe_then_denied", "noid_then_denied")
NEUTRAL_OUTCOMES = ("withdrawn", "abandoned")

CONFIDENCE_TIERS = (
    ("audited", 200),         # ≥200 cases — publicly defensible
    ("preliminary", 50),       # 50-199 cases — directional
    ("insufficient", 0),       # <50 cases — not published
)


def _tier_for(case_count: int) -> str:
    for label, threshold in CONFIDENCE_TIERS:
        if case_count >= threshold:
            return label
    return "insufficient"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ApprovalIndexService:
    """Audited approval-rate index by visa × country × service center × attorney."""

    MIN_SLICE_SIZE_FOR_PUBLISHING = 5    # statistical privacy floor

    def __init__(self, case_workspace: Any | None = None) -> None:
        self._cases = case_workspace
        self._outcomes: dict[str, dict] = {}        # outcome_id → record
        self._snapshots: dict[str, dict] = {}        # snapshot_id → published Index
        self._latest_snapshot_id: str | None = None

    # ---------- recording outcomes ----------
    def record_outcome(
        self,
        workspace_id: str,
        visa_type: str,
        country: str,
        outcome: str,
        decision_date: str,
        attorney_id: str | None = None,
        service_center: str | None = None,
        rfe_count: int = 0,
        time_to_decision_days: int | None = None,
        government_fee_usd: float | None = None,
        attorney_fee_usd: float | None = None,
        applicant_country_of_birth: str | None = None,
    ) -> dict:
        if outcome not in OUTCOMES:
            raise ValueError(f"Unknown outcome: {outcome}")
        outcome_id = str(uuid.uuid4())
        record = {
            "id": outcome_id,
            "workspace_id": workspace_id,
            "visa_type": visa_type,
            "country": country,
            "outcome": outcome,
            "decision_date": decision_date,
            "attorney_id": attorney_id,
            "service_center": service_center,
            "rfe_count": rfe_count,
            "time_to_decision_days": time_to_decision_days,
            "government_fee_usd": government_fee_usd,
            "attorney_fee_usd": attorney_fee_usd,
            "applicant_country_of_birth": applicant_country_of_birth,
            "recorded_at": datetime.utcnow().isoformat(),
        }
        self._outcomes[outcome_id] = record
        return record

    def list_outcomes(
        self,
        visa_type: str | None = None,
        country: str | None = None,
        service_center: str | None = None,
        attorney_id: str | None = None,
        since: str | None = None,
        outcome: str | None = None,
    ) -> list[dict]:
        out = list(self._outcomes.values())
        if visa_type:
            out = [o for o in out if o["visa_type"] == visa_type]
        if country:
            out = [o for o in out if o["country"] == country]
        if service_center:
            out = [o for o in out if o.get("service_center") == service_center]
        if attorney_id:
            out = [o for o in out if o.get("attorney_id") == attorney_id]
        if since:
            out = [o for o in out if o["decision_date"] >= since]
        if outcome:
            out = [o for o in out if o["outcome"] == outcome]
        return out

    # ---------- index computation ----------
    def compute_slice(
        self,
        visa_type: str | None = None,
        country: str | None = None,
        service_center: str | None = None,
        attorney_id: str | None = None,
        since: str | None = None,
    ) -> dict:
        """Compute the approval rate + statistics for a single slice."""
        outcomes = self.list_outcomes(
            visa_type=visa_type, country=country,
            service_center=service_center, attorney_id=attorney_id,
            since=since,
        )
        n = len(outcomes)
        positive = sum(1 for o in outcomes if o["outcome"] in POSITIVE_OUTCOMES)
        negative = sum(1 for o in outcomes if o["outcome"] in NEGATIVE_OUTCOMES)
        neutral = sum(1 for o in outcomes if o["outcome"] in NEUTRAL_OUTCOMES)

        # Privacy floor — never expose <5 cases
        if n < self.MIN_SLICE_SIZE_FOR_PUBLISHING:
            return {
                "slice": {"visa_type": visa_type, "country": country,
                          "service_center": service_center, "attorney_id": attorney_id},
                "case_count": n,
                "tier": "insufficient",
                "publishable": False,
                "reason": f"Below the {self.MIN_SLICE_SIZE_FOR_PUBLISHING}-case privacy floor",
            }

        # Approval rate calculations (excluding withdrawn/abandoned from denominator)
        decided = positive + negative
        if decided == 0:
            approval_rate = None
            confidence_low = confidence_high = None
        else:
            approval_rate = positive / decided
            # Wilson confidence interval (95%)
            z = 1.96
            denom = 1 + z**2 / decided
            center = approval_rate + z**2 / (2 * decided)
            offset = z * math.sqrt(approval_rate * (1 - approval_rate) / decided + z**2 / (4 * decided**2))
            confidence_low = max(0.0, (center - offset) / denom)
            confidence_high = min(1.0, (center + offset) / denom)

        # Time-to-decision stats
        ttds = [o["time_to_decision_days"] for o in outcomes if o.get("time_to_decision_days")]
        ttd_median = int(statistics.median(ttds)) if ttds else None
        ttd_mean = int(statistics.mean(ttds)) if ttds else None
        ttd_p90 = int(_percentile(ttds, 90)) if len(ttds) >= 5 else None

        # RFE rate
        rfe_count = sum(1 for o in outcomes if o.get("rfe_count", 0) > 0)
        rfe_rate = rfe_count / n if n else None

        return {
            "slice": {"visa_type": visa_type, "country": country,
                      "service_center": service_center, "attorney_id": attorney_id},
            "case_count": n,
            "decided_count": decided,
            "approved_count": positive,
            "denied_count": negative,
            "neutral_count": neutral,
            "approval_rate": round(approval_rate, 4) if approval_rate is not None else None,
            "approval_rate_pct": round(approval_rate * 100, 1) if approval_rate is not None else None,
            "confidence_interval_95_pct": (
                [round(confidence_low * 100, 1), round(confidence_high * 100, 1)]
                if confidence_low is not None else None
            ),
            "rfe_rate_pct": round(rfe_rate * 100, 1) if rfe_rate is not None else None,
            "time_to_decision_median_days": ttd_median,
            "time_to_decision_mean_days": ttd_mean,
            "time_to_decision_p90_days": ttd_p90,
            "tier": _tier_for(n),
            "publishable": _tier_for(n) != "insufficient",
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- snapshot publication ----------
    def publish_snapshot(self, label: str = "", since_months: int | None = None) -> dict:
        """Build the full Index across every visa-type × country slice with enough data
        and store as a published snapshot."""
        since = None
        if since_months:
            since = (date.today() - timedelta(days=30 * since_months)).isoformat()

        # Discover all distinct visa × country combinations with at least one outcome
        combos: set[tuple[str, str]] = set()
        all_outcomes = self.list_outcomes(since=since)
        for o in all_outcomes:
            combos.add((o["visa_type"], o["country"]))

        slices = []
        for visa_type, country in sorted(combos):
            slice_data = self.compute_slice(visa_type=visa_type, country=country, since=since)
            if slice_data["publishable"]:
                slices.append(slice_data)
            # Also compute per-service-center if any data
            sc_set = {o.get("service_center") for o in self.list_outcomes(visa_type=visa_type, country=country, since=since) if o.get("service_center")}
            for sc in sc_set:
                sc_slice = self.compute_slice(visa_type=visa_type, country=country, service_center=sc, since=since)
                if sc_slice["publishable"]:
                    slices.append(sc_slice)

        snapshot = {
            "id": str(uuid.uuid4()),
            "label": label or f"Approval Index {date.today().isoformat()}",
            "since": since,
            "total_outcomes_in_window": len(all_outcomes),
            "slice_count": len(slices),
            "slices": slices,
            "published_at": datetime.utcnow().isoformat(),
            "method_notes": (
                "Approval rate = (approved + RFE-then-approved + NOID-then-approved) / "
                "(approved + denied + RFE-then-denied + NOID-then-denied). Withdrawn and "
                "abandoned cases excluded from rate denominator. 95% Wilson confidence interval. "
                f"Privacy floor: slices with fewer than {self.MIN_SLICE_SIZE_FOR_PUBLISHING} "
                "cases never published. Tier: audited (>=200), preliminary (50-199), "
                "insufficient (<50)."
            ),
        }
        self._snapshots[snapshot["id"]] = snapshot
        self._latest_snapshot_id = snapshot["id"]
        return snapshot

    def get_snapshot(self, snapshot_id: str) -> dict | None:
        return self._snapshots.get(snapshot_id)

    def get_latest_snapshot(self) -> dict | None:
        if self._latest_snapshot_id:
            return self._snapshots.get(self._latest_snapshot_id)
        return None

    def list_snapshots(self, limit: int = 20) -> list[dict]:
        snaps = sorted(self._snapshots.values(), key=lambda s: s["published_at"], reverse=True)
        return snaps[:limit]

    # ---------- attorney scorecard ----------
    def attorney_scorecard(self, attorney_id: str, since_months: int = 24) -> dict:
        """Compute per-attorney approval performance for marketplace ranking."""
        since = (date.today() - timedelta(days=30 * since_months)).isoformat()
        outcomes = self.list_outcomes(attorney_id=attorney_id, since=since)
        n = len(outcomes)
        if n == 0:
            return {
                "attorney_id": attorney_id,
                "case_count": 0,
                "tier": "insufficient",
                "scorecard_publishable": False,
            }
        # By visa type
        by_visa: dict[str, dict] = {}
        for o in outcomes:
            v = o["visa_type"]
            if v not in by_visa:
                by_visa[v] = {"count": 0, "approved": 0, "rfe": 0}
            by_visa[v]["count"] += 1
            if o["outcome"] in POSITIVE_OUTCOMES:
                by_visa[v]["approved"] += 1
            if o.get("rfe_count", 0) > 0:
                by_visa[v]["rfe"] += 1
        for v in by_visa:
            by_visa[v]["approval_rate_pct"] = round(by_visa[v]["approved"] / by_visa[v]["count"] * 100, 1)
            by_visa[v]["rfe_rate_pct"] = round(by_visa[v]["rfe"] / by_visa[v]["count"] * 100, 1)

        # Overall
        positive = sum(1 for o in outcomes if o["outcome"] in POSITIVE_OUTCOMES)
        negative = sum(1 for o in outcomes if o["outcome"] in NEGATIVE_OUTCOMES)
        decided = positive + negative
        rate = positive / decided if decided else None
        return {
            "attorney_id": attorney_id,
            "since": since,
            "case_count": n,
            "decided_count": decided,
            "overall_approval_rate_pct": round(rate * 100, 1) if rate is not None else None,
            "by_visa_type": by_visa,
            "tier": _tier_for(n),
            "scorecard_publishable": n >= self.MIN_SLICE_SIZE_FOR_PUBLISHING,
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- introspection ----------
    @staticmethod
    def list_outcome_kinds() -> list[str]:
        return list(OUTCOMES)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)
