"""Outcome-Tied Pricing Telemetry — anonymized fee + timeline aggregation.

The killer applicant-side number: "What does an O-1 actually cost in 2026, in
real dollars and real days, based on closed cases at firms like the ones we
match you with?"

Aggregates from the same outcome stream that feeds the Approval Index.
Anonymizes by enforcing a privacy floor (≥10 cases per slice) and never
exposes individual fees.

Provides:
  - median attorney fee by visa type × country
  - p25 / p75 / p90 ranges (where the typical applicant lands)
  - median government fee + breakdown
  - median time-to-decision
  - cost-vs-timeline tradeoff (premium processing economics)
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any


PRIVACY_FLOOR = 10


class OutcomeTelemetryService:
    """Anonymized fee + timeline telemetry across closed cases."""

    def __init__(self, approval_index_service: Any | None = None) -> None:
        self._approval_index = approval_index_service
        self._published: dict[str, dict] = {}

    def compute_pricing_for_slice(
        self,
        visa_type: str,
        country: str = "US",
        since_months: int = 24,
        country_of_birth: str | None = None,
    ) -> dict:
        if self._approval_index is None:
            return {"error": "Approval Index service not wired"}
        since = (date.today() - timedelta(days=30 * since_months)).isoformat()
        outcomes = self._approval_index.list_outcomes(
            visa_type=visa_type, country=country, since=since,
        )
        if country_of_birth:
            outcomes = [o for o in outcomes if o.get("applicant_country_of_birth") == country_of_birth]

        n = len(outcomes)
        if n < PRIVACY_FLOOR:
            return {
                "slice": {"visa_type": visa_type, "country": country,
                          "country_of_birth": country_of_birth},
                "case_count": n,
                "publishable": False,
                "reason": f"Below the {PRIVACY_FLOOR}-case privacy floor",
            }

        attorney_fees = [o["attorney_fee_usd"] for o in outcomes if o.get("attorney_fee_usd")]
        gov_fees = [o["government_fee_usd"] for o in outcomes if o.get("government_fee_usd")]
        ttds = [o["time_to_decision_days"] for o in outcomes if o.get("time_to_decision_days")]

        return {
            "slice": {"visa_type": visa_type, "country": country,
                      "country_of_birth": country_of_birth},
            "case_count": n,
            "since": since,
            "attorney_fee": _stats_block(attorney_fees) if len(attorney_fees) >= PRIVACY_FLOOR else None,
            "government_fee": _stats_block(gov_fees) if len(gov_fees) >= PRIVACY_FLOOR else None,
            "total_fee_estimate_usd": _combined_total(attorney_fees, gov_fees) if attorney_fees and gov_fees else None,
            "time_to_decision": _stats_block(ttds, unit="days") if len(ttds) >= PRIVACY_FLOOR else None,
            "publishable": True,
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": (
                "Anonymized aggregates only — individual fees, attorney fees, "
                "and case identities are never exposed. Government fees from "
                "official USCIS / DOL / DOS schedules. Attorney fees are "
                "reported voluntarily and may not represent the full market."
            ),
        }

    def applicant_pricing_estimate(
        self, visa_type: str, country: str = "US",
        country_of_birth: str | None = None,
    ) -> dict:
        """Public-facing pricing estimate — what an applicant would see during
        intake."""
        agg = self.compute_pricing_for_slice(visa_type, country, country_of_birth=country_of_birth)
        if not agg.get("publishable"):
            return {
                "visa_type": visa_type, "country": country,
                "estimate_available": False,
                "explanation": "We don't yet have enough closed-case data to publish a verified estimate for this slice.",
            }
        atty = agg.get("attorney_fee") or {}
        gov = agg.get("government_fee") or {}
        ttd = agg.get("time_to_decision") or {}
        return {
            "visa_type": visa_type,
            "country": country,
            "country_of_birth": country_of_birth,
            "estimate_available": True,
            "based_on_cases": agg["case_count"],
            "attorney_fee_typical_range_usd": (
                [int(atty["p25"]), int(atty["p75"])] if atty else None
            ),
            "attorney_fee_median_usd": int(atty["median"]) if atty else None,
            "government_fee_typical_usd": int(gov["median"]) if gov else None,
            "total_typical_range_usd": (
                [int(atty["p25"] + gov["median"]), int(atty["p75"] + gov["median"])]
                if atty and gov else None
            ),
            "time_to_decision_typical_days": (
                [int(ttd["p25"]), int(ttd["p75"])] if ttd else None
            ),
            "time_to_decision_median_days": int(ttd["median"]) if ttd else None,
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": agg["disclosure"],
        }

    def publish_pricing_index(self, since_months: int = 24) -> dict:
        """Build the full applicant-facing pricing index across visa types
        with enough closed cases."""
        if self._approval_index is None:
            return {"error": "Approval Index service not wired"}
        # Use whatever visa/country combos exist in the outcome data
        all_outcomes = self._approval_index.list_outcomes()
        combos = {(o["visa_type"], o["country"]) for o in all_outcomes}
        rows = []
        for visa, country in sorted(combos):
            est = self.applicant_pricing_estimate(visa, country)
            if est.get("estimate_available"):
                rows.append(est)
        index = {
            "id": str(uuid.uuid4()),
            "since_months": since_months,
            "row_count": len(rows),
            "rows": rows,
            "published_at": datetime.utcnow().isoformat(),
        }
        self._published[index["id"]] = index
        return index

    def list_published(self, limit: int = 20) -> list[dict]:
        return sorted(self._published.values(), key=lambda x: x["published_at"], reverse=True)[:limit]


def _stats_block(values: list[float], unit: str = "usd") -> dict:
    if not values:
        return {}
    return {
        "n": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "median": round(statistics.median(values), 2),
        "mean": round(statistics.mean(values), 2),
        "p25": round(_percentile(values, 25), 2),
        "p75": round(_percentile(values, 75), 2),
        "p90": round(_percentile(values, 90), 2),
        "unit": unit,
    }


def _combined_total(attorney_fees: list[float], gov_fees: list[float]) -> dict:
    median = statistics.median(attorney_fees) + statistics.median(gov_fees)
    p75 = _percentile(attorney_fees, 75) + _percentile(gov_fees, 75)
    p25 = _percentile(attorney_fees, 25) + _percentile(gov_fees, 25)
    return {
        "median_usd": round(median, 2),
        "p25_usd": round(p25, 2),
        "p75_usd": round(p75, 2),
    }


def _percentile(values: list[float], p: float) -> float:
    import math
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)
