"""Embassy Intelligence — structured consular post data.

The data nobody has structured. Wait times, interview difficulty, document quirks,
and recent rejection patterns scattered across Reddit, Trackitt, attorney forums,
and applicant chatter — aggregated and queryable.

Each post (consulate / embassy) has:
  - location, country, type
  - typical wait time bands (interview slot vs. visa-ready)
  - approval-trend signal (improving / stable / tightening)
  - common document quirks (post-specific birth-cert rules, tax-return demands)
  - recent rejection patterns (categorized)
  - language requirements at the post
  - notable practices (e.g. some posts require translated certificates from a
    specific list of approved translators only)

Crowdsourced reports + attorney annotations augment the seed data. Reports
require a verified attorney or applicant to register and accumulate over time
to upgrade the post's signal weight.

This service does NOT make predictions about specific applicants — it surfaces
the structured intelligence so attorneys (and the strategy optimizer) can use
it.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Post catalog (seed — high-volume immigration consular posts)
# ---------------------------------------------------------------------------

POSTS_SEED: list[dict[str, Any]] = [
    # ---- US consulates worldwide ----
    {"id": "us-mumbai", "name": "U.S. Consulate General Mumbai", "country_iso": "IN", "type": "consulate",
     "operates_for": "US", "city": "Mumbai", "categories": ["F-1", "H-1B", "B-1/B-2", "L-1"],
     "languages": ["English", "Hindi", "Marathi"], "primary_load": "students_workers"},
    {"id": "us-chennai", "name": "U.S. Consulate General Chennai", "country_iso": "IN", "type": "consulate",
     "operates_for": "US", "city": "Chennai", "categories": ["F-1", "H-1B", "B-1/B-2", "H-4"],
     "languages": ["English", "Tamil"], "primary_load": "students_workers"},
    {"id": "us-hyderabad", "name": "U.S. Consulate General Hyderabad", "country_iso": "IN", "type": "consulate",
     "operates_for": "US", "city": "Hyderabad", "categories": ["F-1", "H-1B"],
     "languages": ["English", "Telugu"], "primary_load": "tech_workers"},
    {"id": "us-delhi", "name": "U.S. Embassy New Delhi", "country_iso": "IN", "type": "embassy",
     "operates_for": "US", "city": "New Delhi", "categories": ["B-1/B-2", "F-1", "H-1B", "L-1"],
     "languages": ["English", "Hindi"], "primary_load": "mixed"},
    {"id": "us-beijing", "name": "U.S. Embassy Beijing", "country_iso": "CN", "type": "embassy",
     "operates_for": "US", "city": "Beijing", "categories": ["F-1", "B-1/B-2", "H-1B", "EB-5"],
     "languages": ["English", "Mandarin"], "primary_load": "students_investors"},
    {"id": "us-shanghai", "name": "U.S. Consulate General Shanghai", "country_iso": "CN", "type": "consulate",
     "operates_for": "US", "city": "Shanghai", "categories": ["F-1", "B-1/B-2", "L-1"],
     "languages": ["English", "Mandarin"], "primary_load": "mixed"},
    {"id": "us-guangzhou", "name": "U.S. Consulate General Guangzhou", "country_iso": "CN", "type": "consulate",
     "operates_for": "US", "city": "Guangzhou", "categories": ["IR-1", "K-1", "CR-1", "F-1"],
     "languages": ["English", "Mandarin", "Cantonese"], "primary_load": "immigrant_visas"},
    {"id": "us-mexico-city", "name": "U.S. Embassy Mexico City", "country_iso": "MX", "type": "embassy",
     "operates_for": "US", "city": "Mexico City", "categories": ["B-1/B-2", "TN", "K-1", "IR-1"],
     "languages": ["English", "Spanish"], "primary_load": "mixed"},
    {"id": "us-juarez", "name": "U.S. Consulate General Ciudad Juárez", "country_iso": "MX", "type": "consulate",
     "operates_for": "US", "city": "Ciudad Juárez", "categories": ["IR-1", "CR-1", "K-1"],
     "languages": ["English", "Spanish"], "primary_load": "immigrant_visas"},
    {"id": "us-manila", "name": "U.S. Embassy Manila", "country_iso": "PH", "type": "embassy",
     "operates_for": "US", "city": "Manila", "categories": ["F-1", "B-1/B-2", "K-1", "IR-1"],
     "languages": ["English", "Tagalog"], "primary_load": "mixed"},
    {"id": "us-lagos", "name": "U.S. Consulate General Lagos", "country_iso": "NG", "type": "consulate",
     "operates_for": "US", "city": "Lagos", "categories": ["F-1", "B-1/B-2", "DV"],
     "languages": ["English"], "primary_load": "students"},
    {"id": "us-lima", "name": "U.S. Embassy Lima", "country_iso": "PE", "type": "embassy",
     "operates_for": "US", "city": "Lima", "categories": ["F-1", "B-1/B-2"],
     "languages": ["English", "Spanish"], "primary_load": "students"},
    {"id": "us-london", "name": "U.S. Embassy London", "country_iso": "GB", "type": "embassy",
     "operates_for": "US", "city": "London", "categories": ["E-2", "L-1", "B-1/B-2"],
     "languages": ["English"], "primary_load": "investors_workers"},
    # ---- UK + Commonwealth ----
    {"id": "uk-mumbai", "name": "UK Visa Application Centre Mumbai", "country_iso": "IN", "type": "vac",
     "operates_for": "UK", "city": "Mumbai", "categories": ["Student", "Skilled Worker", "Visitor"],
     "languages": ["English", "Hindi"], "primary_load": "students_workers"},
    {"id": "uk-delhi", "name": "UK Visa Application Centre New Delhi", "country_iso": "IN", "type": "vac",
     "operates_for": "UK", "city": "New Delhi", "categories": ["Student", "Skilled Worker"],
     "languages": ["English", "Hindi"], "primary_load": "students_workers"},
    # ---- Canada ----
    {"id": "ca-delhi", "name": "VAC New Delhi (Canada)", "country_iso": "IN", "type": "vac",
     "operates_for": "CA", "city": "New Delhi", "categories": ["Study Permit", "Work Permit", "TRV"],
     "languages": ["English", "Hindi"], "primary_load": "students_workers"},
    {"id": "ca-chandigarh", "name": "VAC Chandigarh (Canada)", "country_iso": "IN", "type": "vac",
     "operates_for": "CA", "city": "Chandigarh", "categories": ["Study Permit", "Work Permit"],
     "languages": ["English", "Punjabi"], "primary_load": "students"},
    # ---- Australia ----
    {"id": "au-shanghai", "name": "Australian Visa Office Shanghai", "country_iso": "CN", "type": "vac",
     "operates_for": "AU", "city": "Shanghai", "categories": ["subclass 500", "subclass 482"],
     "languages": ["English", "Mandarin"], "primary_load": "students"},
    # ---- Germany ----
    {"id": "de-mumbai", "name": "German Consulate General Mumbai", "country_iso": "IN", "type": "consulate",
     "operates_for": "DE", "city": "Mumbai", "categories": ["Student", "EU Blue Card"],
     "languages": ["English", "German", "Hindi"], "primary_load": "students_workers"},
]


REPORT_KINDS = (
    "wait_time", "rejection_pattern", "document_quirk",
    "interview_practice", "approval_trend", "general_intel",
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EmbassyIntelService:
    """Structured embassy / consular post intelligence."""

    def __init__(self) -> None:
        self._posts: dict[str, dict] = {p["id"]: p for p in POSTS_SEED}
        self._reports: list[dict] = []      # crowdsourced reports
        self._wait_times: dict[str, list[dict]] = {}   # post_id → wait time samples

    # ---------- post discovery ----------
    @staticmethod
    def list_destination_countries() -> list[str]:
        return sorted({p["operates_for"] for p in POSTS_SEED})

    def list_posts(
        self,
        operates_for: str | None = None,
        country_iso: str | None = None,
        category: str | None = None,
    ) -> list[dict]:
        out = list(self._posts.values())
        if operates_for:
            out = [p for p in out if p["operates_for"] == operates_for]
        if country_iso:
            out = [p for p in out if p["country_iso"] == country_iso]
        if category:
            out = [p for p in out if any(c.lower() == category.lower() for c in p["categories"])]
        return out

    def get_post(self, post_id: str) -> dict | None:
        return self._posts.get(post_id)

    def add_post(self, post_data: dict) -> dict:
        if "id" not in post_data:
            post_data["id"] = str(uuid.uuid4())
        self._posts[post_data["id"]] = post_data
        return post_data

    # ---------- crowdsourced reports ----------
    def submit_report(
        self,
        post_id: str,
        kind: str,
        body: str,
        category_visa: str | None = None,
        reporter_id: str | None = None,
        reporter_role: str = "applicant",   # "applicant" | "attorney" | "verified_attorney"
        observed_at: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        if post_id not in self._posts:
            raise ValueError(f"Unknown post: {post_id}")
        if kind not in REPORT_KINDS:
            raise ValueError(f"Unknown report kind: {kind}")
        weight = {"applicant": 1, "attorney": 3, "verified_attorney": 5}.get(reporter_role, 1)
        record = {
            "id": str(uuid.uuid4()),
            "post_id": post_id, "kind": kind, "body": body,
            "category_visa": category_visa,
            "reporter_id": reporter_id, "reporter_role": reporter_role,
            "weight": weight,
            "observed_at": observed_at or datetime.utcnow().date().isoformat(),
            "submitted_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
            "verified": reporter_role == "verified_attorney",
        }
        self._reports.append(record)
        return record

    def list_reports(
        self,
        post_id: str | None = None,
        kind: str | None = None,
        category_visa: str | None = None,
        since: str | None = None,
        verified_only: bool = False,
    ) -> list[dict]:
        out = self._reports
        if post_id:
            out = [r for r in out if r["post_id"] == post_id]
        if kind:
            out = [r for r in out if r["kind"] == kind]
        if category_visa:
            out = [r for r in out if r.get("category_visa") == category_visa]
        if since:
            out = [r for r in out if r["observed_at"] >= since]
        if verified_only:
            out = [r for r in out if r["verified"]]
        return sorted(out, key=lambda r: (-r["weight"], r["observed_at"]), reverse=True)

    # ---------- wait times ----------
    def submit_wait_time(
        self,
        post_id: str,
        days_to_appointment: int,
        category_visa: str,
        reporter_role: str = "applicant",
    ) -> dict:
        if post_id not in self._posts:
            raise ValueError(f"Unknown post: {post_id}")
        if days_to_appointment < 0:
            raise ValueError("Days to appointment must be non-negative")
        weight = {"applicant": 1, "attorney": 3, "verified_attorney": 5}.get(reporter_role, 1)
        record = {
            "id": str(uuid.uuid4()),
            "post_id": post_id,
            "category_visa": category_visa,
            "days_to_appointment": days_to_appointment,
            "reporter_role": reporter_role, "weight": weight,
            "submitted_at": datetime.utcnow().isoformat(),
        }
        self._wait_times.setdefault(post_id, []).append(record)
        return record

    def get_wait_time_stats(
        self, post_id: str, category_visa: str | None = None,
        recent_days: int = 90,
    ) -> dict:
        samples = self._wait_times.get(post_id, [])
        cutoff = (date.today() - timedelta(days=recent_days)).isoformat()
        samples = [s for s in samples if s["submitted_at"] >= cutoff]
        if category_visa:
            samples = [s for s in samples if s["category_visa"] == category_visa]
        if not samples:
            return {"post_id": post_id, "category_visa": category_visa,
                    "samples": 0, "publishable": False}
        days_values = [s["days_to_appointment"] for s in samples]
        return {
            "post_id": post_id,
            "category_visa": category_visa,
            "samples": len(samples),
            "median_days": int(statistics.median(days_values)),
            "p25_days": int(_percentile(days_values, 25)),
            "p75_days": int(_percentile(days_values, 75)),
            "p90_days": int(_percentile(days_values, 90)),
            "min_days": min(days_values),
            "max_days": max(days_values),
            "recent_days_window": recent_days,
            "publishable": len(samples) >= 5,
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- post intelligence summary ----------
    def post_summary(self, post_id: str, category_visa: str | None = None) -> dict:
        post = self._posts.get(post_id)
        if post is None:
            raise ValueError(f"Unknown post: {post_id}")
        wait_stats = self.get_wait_time_stats(post_id, category_visa=category_visa)
        reports = self.list_reports(post_id=post_id, category_visa=category_visa)
        # Group reports by kind
        by_kind: dict[str, list[dict]] = {}
        for r in reports:
            by_kind.setdefault(r["kind"], []).append(r)
        # Recent rejection-pattern signals
        rejection_patterns = by_kind.get("rejection_pattern", [])[:5]
        # Document quirks
        document_quirks = by_kind.get("document_quirk", [])[:5]
        # Approval trend
        trend_reports = by_kind.get("approval_trend", [])
        return {
            "post": post,
            "category_visa": category_visa,
            "wait_time_stats": wait_stats,
            "rejection_patterns_recent": rejection_patterns,
            "document_quirks": document_quirks,
            "approval_trend_reports": trend_reports[:3],
            "report_counts_by_kind": {k: len(v) for k, v in by_kind.items()},
            "total_reports": len(reports),
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- introspection ----------
    @staticmethod
    def list_report_kinds() -> list[str]:
        return list(REPORT_KINDS)

    @staticmethod
    def list_seed_post_count() -> int:
        return len(POSTS_SEED)


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
