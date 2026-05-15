"""Priority Date Forecaster — when will my priority date become current?

The Visa Bulletin moves chargeability cutoff dates forward (and sometimes
backward) every month. For employment-based and family-based applicants,
"when does my priority date become current" is the single most important
question of their immigration journey.

This service:
  - Maintains a hand-curated history of Final Action Dates per category
  - Computes per-month movement velocity (days per month) for each category
  - Linearly extrapolates to estimate when a given priority date will become
    current
  - Surfaces uncertainty bands (slow / typical / fast scenarios)
  - Refuses to publish a forecast when historical movement is too volatile

Categories supported in the seed corpus: EB-1, EB-2, EB-3, F1, F2A, F2B, F3,
F4 — for the four chargeability buckets that matter most: All Other / India /
China / Mexico / Philippines (for family).
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any


CATEGORIES = (
    "EB-1", "EB-2", "EB-3", "EB-4", "EB-5",
    "F1", "F2A", "F2B", "F3", "F4",
)

CHARGEABILITIES = (
    "All Other", "India", "China-mainland born", "Mexico", "Philippines",
)


# Hand-curated seed: monthly Final Action Dates from Aug 2024 through Apr 2026.
# Format: (bulletin_month_iso, category, chargeability, final_action_date)
# Where status is "Current" we encode as "9999-12-31" sentinel.
# Where status is "Unavailable" we encode as None.
SEED_HISTORY: list[tuple[str, str, str, str | None]] = [
    # ---- EB-1 ----
    ("2024-08-01", "EB-1", "All Other", "9999-12-31"),
    ("2024-09-01", "EB-1", "All Other", "9999-12-31"),
    ("2024-10-01", "EB-1", "All Other", "9999-12-31"),
    ("2024-11-01", "EB-1", "All Other", "9999-12-31"),
    ("2024-12-01", "EB-1", "All Other", "9999-12-31"),
    ("2025-01-01", "EB-1", "All Other", "9999-12-31"),
    ("2025-02-01", "EB-1", "All Other", "9999-12-31"),
    ("2025-03-01", "EB-1", "All Other", "9999-12-31"),
    ("2025-04-01", "EB-1", "All Other", "9999-12-31"),
    ("2024-08-01", "EB-1", "India", "2022-02-01"),
    ("2024-09-01", "EB-1", "India", "2022-02-01"),
    ("2024-10-01", "EB-1", "India", "2022-02-01"),
    ("2024-11-01", "EB-1", "India", "2022-02-01"),
    ("2024-12-01", "EB-1", "India", "2022-02-15"),
    ("2025-01-01", "EB-1", "India", "2022-02-15"),
    ("2025-02-01", "EB-1", "India", "2022-02-15"),
    ("2025-03-01", "EB-1", "India", "2022-04-15"),
    ("2025-04-01", "EB-1", "India", "2022-05-15"),
    # ---- EB-2 ----
    ("2024-08-01", "EB-2", "All Other", "2023-03-15"),
    ("2024-09-01", "EB-2", "All Other", "2023-03-15"),
    ("2024-10-01", "EB-2", "All Other", "2023-03-15"),
    ("2024-11-01", "EB-2", "All Other", "2023-04-01"),
    ("2024-12-01", "EB-2", "All Other", "2023-04-01"),
    ("2025-01-01", "EB-2", "All Other", "2023-05-15"),
    ("2025-02-01", "EB-2", "All Other", "2023-06-22"),
    ("2025-03-01", "EB-2", "All Other", "2023-07-22"),
    ("2025-04-01", "EB-2", "All Other", "2023-09-01"),
    ("2024-08-01", "EB-2", "India", "2012-07-15"),
    ("2024-09-01", "EB-2", "India", "2012-07-15"),
    ("2024-10-01", "EB-2", "India", "2012-07-15"),
    ("2024-11-01", "EB-2", "India", "2012-08-01"),
    ("2024-12-01", "EB-2", "India", "2012-08-01"),
    ("2025-01-01", "EB-2", "India", "2012-09-01"),
    ("2025-02-01", "EB-2", "India", "2012-09-22"),
    ("2025-03-01", "EB-2", "India", "2012-10-15"),
    ("2025-04-01", "EB-2", "India", "2012-11-08"),
    ("2024-08-01", "EB-2", "China-mainland born", "2020-03-22"),
    ("2024-09-01", "EB-2", "China-mainland born", "2020-03-22"),
    ("2024-10-01", "EB-2", "China-mainland born", "2020-04-15"),
    ("2024-11-01", "EB-2", "China-mainland born", "2020-04-15"),
    ("2024-12-01", "EB-2", "China-mainland born", "2020-04-22"),
    ("2025-01-01", "EB-2", "China-mainland born", "2020-05-15"),
    ("2025-02-01", "EB-2", "China-mainland born", "2020-06-08"),
    ("2025-03-01", "EB-2", "China-mainland born", "2020-07-08"),
    ("2025-04-01", "EB-2", "China-mainland born", "2020-08-15"),
    # ---- EB-3 ----
    ("2024-08-01", "EB-3", "All Other", "2022-12-01"),
    ("2024-09-01", "EB-3", "All Other", "2022-12-01"),
    ("2024-10-01", "EB-3", "All Other", "2022-12-01"),
    ("2024-11-01", "EB-3", "All Other", "2023-01-01"),
    ("2024-12-01", "EB-3", "All Other", "2023-01-15"),
    ("2025-01-01", "EB-3", "All Other", "2023-02-15"),
    ("2025-02-01", "EB-3", "All Other", "2023-03-15"),
    ("2025-03-01", "EB-3", "All Other", "2023-04-15"),
    ("2025-04-01", "EB-3", "All Other", "2023-05-22"),
    ("2024-08-01", "EB-3", "India", "2012-11-22"),
    ("2024-09-01", "EB-3", "India", "2012-11-22"),
    ("2024-10-01", "EB-3", "India", "2012-12-01"),
    ("2024-11-01", "EB-3", "India", "2012-12-15"),
    ("2024-12-01", "EB-3", "India", "2013-01-01"),
    ("2025-01-01", "EB-3", "India", "2013-01-22"),
    ("2025-02-01", "EB-3", "India", "2013-02-15"),
    ("2025-03-01", "EB-3", "India", "2013-03-08"),
    ("2025-04-01", "EB-3", "India", "2013-04-01"),
    # ---- F2A ----
    ("2024-08-01", "F2A", "All Other", "2024-01-01"),
    ("2024-09-01", "F2A", "All Other", "2024-01-01"),
    ("2024-10-01", "F2A", "All Other", "2024-01-01"),
    ("2024-11-01", "F2A", "All Other", "2024-02-15"),
    ("2024-12-01", "F2A", "All Other", "2024-03-08"),
    ("2025-01-01", "F2A", "All Other", "2024-04-15"),
    ("2025-02-01", "F2A", "All Other", "2024-05-22"),
    ("2025-03-01", "F2A", "All Other", "2024-07-01"),
    ("2025-04-01", "F2A", "All Other", "2024-08-08"),
]


# ---------------------------------------------------------------------------

class PriorityDateForecasterService:
    """Forecast when a priority date becomes current using Visa Bulletin trends."""

    CURRENT_SENTINEL = "9999-12-31"

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []
        for (month, cat, charge, fad) in SEED_HISTORY:
            self._history.append({
                "bulletin_month": month,
                "category": cat,
                "chargeability": charge,
                "final_action_date": fad,
            })
        self._forecasts: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_categories() -> list[str]:
        return list(CATEGORIES)

    @staticmethod
    def list_chargeabilities() -> list[str]:
        return list(CHARGEABILITIES)

    def list_history(
        self, category: str | None = None, chargeability: str | None = None,
    ) -> list[dict]:
        out = self._history
        if category:
            out = [r for r in out if r["category"] == category]
        if chargeability:
            out = [r for r in out if r["chargeability"] == chargeability]
        return sorted(out, key=lambda r: r["bulletin_month"])

    def record_bulletin_month(
        self,
        bulletin_month: str,
        category: str,
        chargeability: str,
        final_action_date: str | None,
    ) -> dict:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        if chargeability not in CHARGEABILITIES:
            raise ValueError(f"Unknown chargeability: {chargeability}")
        record = {
            "bulletin_month": bulletin_month,
            "category": category,
            "chargeability": chargeability,
            "final_action_date": final_action_date,
        }
        self._history.append(record)
        return record

    # ---------- velocity ----------
    def compute_velocity(
        self, category: str, chargeability: str,
        lookback_months: int = 12,
    ) -> dict:
        """Compute average forward movement in days/month over the lookback window."""
        history = self.list_history(category=category, chargeability=chargeability)
        # Filter "Current" sentinels and Unavailable rows
        history = [
            r for r in history
            if r["final_action_date"] not in (None, self.CURRENT_SENTINEL)
        ]
        if len(history) < 2:
            return {
                "category": category, "chargeability": chargeability,
                "lookback_months": lookback_months,
                "data_points": len(history),
                "velocity_days_per_month": None,
                "stable": False,
                "reason": "Not enough non-current data points",
            }
        history = history[-lookback_months:] if len(history) > lookback_months else history
        # Pairwise deltas
        deltas: list[float] = []
        for prev, curr in zip(history, history[1:]):
            d_prev = date.fromisoformat(prev["final_action_date"])
            d_curr = date.fromisoformat(curr["final_action_date"])
            delta_days = (d_curr - d_prev).days
            deltas.append(delta_days)
        if not deltas:
            return {
                "category": category, "chargeability": chargeability,
                "data_points": len(history),
                "velocity_days_per_month": None,
                "stable": False,
                "reason": "No pairwise deltas",
            }
        median_velocity = round(statistics.median(deltas), 1)
        mean_velocity = round(statistics.mean(deltas), 1)
        stdev = round(statistics.stdev(deltas), 1) if len(deltas) > 1 else 0.0
        # Stability = stdev / |mean|; large = volatile
        stability_ratio = stdev / abs(mean_velocity) if mean_velocity else float("inf")
        stable = stability_ratio < 1.5 and len(deltas) >= 3
        return {
            "category": category, "chargeability": chargeability,
            "lookback_months": lookback_months,
            "data_points": len(history),
            "deltas_days": deltas,
            "velocity_days_per_month_mean": mean_velocity,
            "velocity_days_per_month_median": median_velocity,
            "velocity_stdev_days": stdev,
            "stable": stable,
            "stability_ratio": round(stability_ratio, 2) if stability_ratio != float("inf") else None,
        }

    # ---------- forecast ----------
    def forecast(
        self,
        category: str,
        chargeability: str,
        priority_date: str,
        as_of: str | None = None,
        lookback_months: int = 12,
    ) -> dict:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category: {category}")
        if chargeability not in CHARGEABILITIES:
            raise ValueError(f"Unknown chargeability: {chargeability}")
        as_of = as_of or date.today().isoformat()
        velocity = self.compute_velocity(category, chargeability, lookback_months)
        # Latest known FAD
        latest = sorted(
            [r for r in self.list_history(category=category, chargeability=chargeability)
             if r["final_action_date"] not in (None,)],
            key=lambda r: r["bulletin_month"],
        )
        if not latest:
            return self._unforecastable(category, chargeability, priority_date,
                                         "No historical data")
        latest_row = latest[-1]
        latest_fad = latest_row["final_action_date"]
        if latest_fad == self.CURRENT_SENTINEL:
            return {
                "category": category, "chargeability": chargeability,
                "priority_date": priority_date,
                "currently_current": True,
                "forecast_status": "current",
                "as_of": as_of,
                "computed_at": datetime.utcnow().isoformat(),
                "disclosure": _DISCLOSURE,
            }
        d_pd = date.fromisoformat(priority_date)
        d_fad = date.fromisoformat(latest_fad)
        if d_pd <= d_fad:
            return {
                "category": category, "chargeability": chargeability,
                "priority_date": priority_date,
                "latest_final_action_date": latest_fad,
                "latest_bulletin_month": latest_row["bulletin_month"],
                "currently_current": True,
                "forecast_status": "already_current",
                "as_of": as_of,
                "computed_at": datetime.utcnow().isoformat(),
                "disclosure": _DISCLOSURE,
            }
        # Need to project forward
        if not velocity["stable"]:
            return {
                "category": category, "chargeability": chargeability,
                "priority_date": priority_date,
                "latest_final_action_date": latest_fad,
                "currently_current": False,
                "forecast_status": "unstable_history",
                "velocity": velocity,
                "reason": "Historical movement is too volatile to publish a forecast",
                "as_of": as_of,
                "computed_at": datetime.utcnow().isoformat(),
                "disclosure": _DISCLOSURE,
            }
        gap_days = (d_pd - d_fad).days
        median_velocity = velocity["velocity_days_per_month_median"]
        mean_velocity = velocity["velocity_days_per_month_mean"]
        # If movement is backward or zero, mark as retrogressed
        if median_velocity <= 0:
            return {
                "category": category, "chargeability": chargeability,
                "priority_date": priority_date,
                "latest_final_action_date": latest_fad,
                "currently_current": False,
                "forecast_status": "retrogressed_or_stalled",
                "velocity": velocity,
                "as_of": as_of,
                "computed_at": datetime.utcnow().isoformat(),
                "disclosure": _DISCLOSURE,
            }
        # Months to current (ETA bands)
        eta_months_typical = round(gap_days / median_velocity, 1)
        # Slow scenario: 1 stdev slower; fast scenario: 1 stdev faster
        slow_v = max(median_velocity - velocity["velocity_stdev_days"], 1)
        fast_v = median_velocity + velocity["velocity_stdev_days"]
        eta_months_slow = round(gap_days / slow_v, 1)
        eta_months_fast = round(gap_days / fast_v, 1) if fast_v > 0 else None

        as_of_dt = date.fromisoformat(as_of)
        eta_typical_dt = as_of_dt + timedelta(days=int(eta_months_typical * 30))
        eta_slow_dt = as_of_dt + timedelta(days=int(eta_months_slow * 30))
        eta_fast_dt = (as_of_dt + timedelta(days=int(eta_months_fast * 30))
                       if eta_months_fast is not None else None)

        forecast_id = str(uuid.uuid4())
        record = {
            "id": forecast_id,
            "category": category, "chargeability": chargeability,
            "priority_date": priority_date,
            "latest_final_action_date": latest_fad,
            "latest_bulletin_month": latest_row["bulletin_month"],
            "currently_current": False,
            "forecast_status": "projected",
            "gap_days": gap_days,
            "velocity": velocity,
            "eta_months_typical": eta_months_typical,
            "eta_months_slow": eta_months_slow,
            "eta_months_fast": eta_months_fast,
            "eta_date_typical": eta_typical_dt.isoformat(),
            "eta_date_slow": eta_slow_dt.isoformat(),
            "eta_date_fast": eta_fast_dt.isoformat() if eta_fast_dt else None,
            "as_of": as_of,
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": _DISCLOSURE,
        }
        self._forecasts[forecast_id] = record
        return record

    @staticmethod
    def _unforecastable(category: str, chargeability: str, priority_date: str,
                        reason: str) -> dict:
        return {
            "category": category, "chargeability": chargeability,
            "priority_date": priority_date,
            "forecast_status": "unforecastable",
            "reason": reason,
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": _DISCLOSURE,
        }

    def get_forecast(self, forecast_id: str) -> dict | None:
        return self._forecasts.get(forecast_id)


_DISCLOSURE = (
    "Forecasts are statistical projections from historical Visa Bulletin movement "
    "and assume continued visa-availability behavior. The Department of State can "
    "retrogress dates without warning when annual quotas are exhausted; any "
    "forecast can be invalidated by a single bulletin. Treat as guidance only — "
    "never as a guarantee."
)
