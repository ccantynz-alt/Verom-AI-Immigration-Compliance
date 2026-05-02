"""Peer Network + CLE Credits — closed forum + tracked continuing-legal-education.

Verified attorneys collaborate in a closed forum on tough cases. Time spent
reviewing peer cases earns Continuing Legal Education (CLE) credit at
participating jurisdictions. The combination — peer learning + free CLE —
is the stickiness mechanism the established players (PLI, AILA) charge for.

Concepts:
  - PeerThread          discussion thread (case strategy, RFE pattern, regulatory
                        update, war story, etc.)
  - PeerComment         comment on a thread, optionally with attached precedent
                        citations from LegalResearchService
  - CLEActivity         time-tracked activity that may be CLE-credit eligible
  - CLECredit           per-attorney record of accumulated credit
  - JurisdictionRule    rule for awarding credit per state bar (each bar has
                        its own credit-hour requirements)

Production: hooks into a CLE credit reporting partner (NACLE, ProLawCLE, etc.).
This implementation provides the activity log + credit accumulation. The
CLE-reporting boundary is the only piece that needs a real-provider swap.
"""

from __future__ import annotations

import statistics
import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

THREAD_KINDS = (
    "case_strategy", "rfe_pattern", "regulatory_update",
    "war_story", "ethics_question", "vendor_recommendation",
    "law_school_thread",
)

CLE_ACTIVITY_KINDS = {
    "thread_review": {
        "label": "Reviewed peer thread",
        "credit_per_minute": 0.005,    # ~3 minutes = 0.015 hours
        "min_minutes_for_credit": 5,
        "max_credit_hours_per_session": 0.25,
    },
    "thread_authorship": {
        "label": "Authored peer thread",
        "credit_per_minute": 0.020,
        "min_minutes_for_credit": 15,
        "max_credit_hours_per_session": 1.0,
    },
    "case_review_response": {
        "label": "Reviewed peer case + posted analysis",
        "credit_per_minute": 0.025,
        "min_minutes_for_credit": 20,
        "max_credit_hours_per_session": 1.5,
    },
    "regulatory_briefing_attendance": {
        "label": "Attended live regulatory briefing",
        "credit_per_minute": 0.0167,   # 1 hour live = 1 credit hour
        "min_minutes_for_credit": 30,
        "max_credit_hours_per_session": 2.0,
    },
    "ethics_discussion": {
        "label": "Ethics discussion participation (CLE Ethics credit)",
        "credit_per_minute": 0.0167,
        "min_minutes_for_credit": 30,
        "max_credit_hours_per_session": 1.0,
        "is_ethics": True,
    },
}

# State bar CLE requirements per credit period (rounded — real rules vary
# considerably by state and renewal cycle).
JURISDICTION_RULES: dict[str, dict[str, Any]] = {
    "NY": {"name": "New York", "credit_hours_required_per_cycle": 24, "cycle_years": 2,
           "ethics_required": 4, "skills_required": 1, "diversity_required": 1,
           "self_study_cap_pct": 50},
    "CA": {"name": "California", "credit_hours_required_per_cycle": 25, "cycle_years": 3,
           "ethics_required": 4, "competence_required": 1, "elimination_of_bias_required": 1},
    "TX": {"name": "Texas", "credit_hours_required_per_cycle": 15, "cycle_years": 1,
           "ethics_required": 3},
    "IL": {"name": "Illinois", "credit_hours_required_per_cycle": 30, "cycle_years": 2,
           "ethics_required": 6},
    "FL": {"name": "Florida", "credit_hours_required_per_cycle": 33, "cycle_years": 3,
           "ethics_required": 5, "tech_required": 3},
    "MA": {"name": "Massachusetts", "credit_hours_required_per_cycle": 0, "cycle_years": 0,
           "note": "Massachusetts has no mandatory CLE."},
    "WA": {"name": "Washington", "credit_hours_required_per_cycle": 45, "cycle_years": 3,
           "ethics_required": 6},
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PeerNetworkService:
    """Verified-attorney peer forum + CLE credit accumulation."""

    def __init__(
        self,
        legal_research_service: Any | None = None,
        team_management_service: Any | None = None,
    ) -> None:
        self._research = legal_research_service
        self._team = team_management_service
        self._threads: dict[str, dict] = {}
        self._comments: dict[str, list[dict]] = {}    # thread_id → comments
        self._activities: list[dict] = []
        self._credit_records: dict[str, list[dict]] = {}    # attorney_id → credits earned
        self._reactions: dict[str, dict[str, set[str]]] = {} # thread_id → reaction → set of user_ids

    # ---------- introspection ----------
    @staticmethod
    def list_thread_kinds() -> list[str]:
        return list(THREAD_KINDS)

    @staticmethod
    def list_jurisdictions() -> list[dict]:
        return [{"code": k, **v} for k, v in JURISDICTION_RULES.items()]

    @staticmethod
    def list_cle_activity_kinds() -> list[dict]:
        return [{"kind": k, **v} for k, v in CLE_ACTIVITY_KINDS.items()]

    # ---------- threads ----------
    def create_thread(
        self,
        author_user_id: str,
        title: str,
        body: str,
        kind: str = "case_strategy",
        tags: list[str] | None = None,
        anonymous: bool = False,
        related_visa_type: str | None = None,
    ) -> dict:
        if kind not in THREAD_KINDS:
            raise ValueError(f"Unknown thread kind: {kind}")
        # In production, verify the author is a verified attorney via team_management
        thread_id = str(uuid.uuid4())
        record = {
            "id": thread_id,
            "author_user_id": None if anonymous else author_user_id,
            "anonymous": anonymous,
            "title": title, "body": body, "kind": kind,
            "tags": tags or [],
            "related_visa_type": related_visa_type,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "comment_count": 0,
            "view_count": 0,
            "is_locked": False,
            "is_pinned": False,
        }
        self._threads[thread_id] = record
        self._comments[thread_id] = []
        return record

    def get_thread(self, thread_id: str, viewer_user_id: str | None = None) -> dict | None:
        thread = self._threads.get(thread_id)
        if thread is None:
            return None
        thread["view_count"] += 1
        # Auto-record a thread_review activity when viewed
        if viewer_user_id:
            self.record_activity(
                attorney_id=viewer_user_id,
                kind="thread_review",
                minutes=3,
                related_thread_id=thread_id,
            )
        return thread

    def list_threads(
        self,
        kind: str | None = None,
        tag: str | None = None,
        related_visa_type: str | None = None,
        author_user_id: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        out = list(self._threads.values())
        if kind:
            out = [t for t in out if t["kind"] == kind]
        if tag:
            out = [t for t in out if tag in t["tags"]]
        if related_visa_type:
            out = [t for t in out if t.get("related_visa_type") == related_visa_type]
        if author_user_id:
            out = [t for t in out if t.get("author_user_id") == author_user_id]
        return sorted(out, key=lambda t: t.get("is_pinned", False), reverse=True)[:limit]

    # ---------- comments ----------
    def post_comment(
        self,
        thread_id: str,
        author_user_id: str,
        body: str,
        anonymous: bool = False,
        cited_authority_ids: list[str] | None = None,
        time_spent_minutes: int = 0,
    ) -> dict:
        thread = self._threads.get(thread_id)
        if thread is None:
            raise ValueError("Thread not found")
        if thread["is_locked"]:
            raise ValueError("Thread is locked")
        # Optionally validate citations
        if cited_authority_ids and self._research:
            for aid in cited_authority_ids:
                if self._research.get_by_id(aid) is None:
                    raise ValueError(f"Citation not found in legal research corpus: {aid}")
        comment_id = str(uuid.uuid4())
        comment = {
            "id": comment_id,
            "thread_id": thread_id,
            "author_user_id": None if anonymous else author_user_id,
            "anonymous": anonymous,
            "body": body,
            "cited_authority_ids": cited_authority_ids or [],
            "posted_at": datetime.utcnow().isoformat(),
        }
        self._comments[thread_id].append(comment)
        thread["comment_count"] += 1
        thread["updated_at"] = comment["posted_at"]
        # Record a CLE activity for the comment if substantive
        if time_spent_minutes >= CLE_ACTIVITY_KINDS["case_review_response"]["min_minutes_for_credit"]:
            self.record_activity(
                attorney_id=author_user_id,
                kind="case_review_response",
                minutes=time_spent_minutes,
                related_thread_id=thread_id,
            )
        return comment

    def list_comments(self, thread_id: str) -> list[dict]:
        return list(self._comments.get(thread_id, []))

    # ---------- reactions ----------
    def react(self, thread_id: str, reaction: str, user_id: str) -> dict:
        if thread_id not in self._threads:
            raise ValueError("Thread not found")
        if reaction not in ("helpful", "thanks", "important", "outdated"):
            raise ValueError(f"Invalid reaction: {reaction}")
        bucket = self._reactions.setdefault(thread_id, {})
        bucket.setdefault(reaction, set()).add(user_id)
        return {
            "thread_id": thread_id,
            "reaction": reaction,
            "count": len(bucket[reaction]),
        }

    def get_reactions(self, thread_id: str) -> dict[str, int]:
        bucket = self._reactions.get(thread_id, {})
        return {r: len(users) for r, users in bucket.items()}

    # ---------- CLE activity tracking ----------
    def record_activity(
        self,
        attorney_id: str,
        kind: str,
        minutes: int,
        related_thread_id: str | None = None,
        related_workspace_id: str | None = None,
        notes: str = "",
    ) -> dict:
        if kind not in CLE_ACTIVITY_KINDS:
            raise ValueError(f"Unknown CLE activity kind: {kind}")
        spec = CLE_ACTIVITY_KINDS[kind]
        activity_id = str(uuid.uuid4())
        record = {
            "id": activity_id,
            "attorney_id": attorney_id,
            "kind": kind,
            "label": spec["label"],
            "minutes": minutes,
            "related_thread_id": related_thread_id,
            "related_workspace_id": related_workspace_id,
            "notes": notes,
            "at": datetime.utcnow().isoformat(),
            "credit_hours_earned": 0.0,
            "is_ethics": spec.get("is_ethics", False),
        }
        # Compute credit (capped per session)
        if minutes >= spec["min_minutes_for_credit"]:
            credit = min(minutes * spec["credit_per_minute"], spec["max_credit_hours_per_session"])
            credit = round(credit, 4)
            record["credit_hours_earned"] = credit
            if credit > 0:
                self._credit_records.setdefault(attorney_id, []).append(record)
        self._activities.append(record)
        return record

    def list_activities(
        self,
        attorney_id: str | None = None,
        kind: str | None = None,
        since: str | None = None,
    ) -> list[dict]:
        out = self._activities
        if attorney_id:
            out = [a for a in out if a["attorney_id"] == attorney_id]
        if kind:
            out = [a for a in out if a["kind"] == kind]
        if since:
            out = [a for a in out if a["at"] >= since]
        return out

    # ---------- CLE credit reporting ----------
    def attorney_cle_summary(
        self, attorney_id: str, jurisdiction: str = "NY",
    ) -> dict:
        rules = JURISDICTION_RULES.get(jurisdiction)
        if rules is None:
            raise ValueError(f"Unknown jurisdiction: {jurisdiction}")
        cycle_years = rules["cycle_years"]
        if cycle_years <= 0:
            cycle_start = None
        else:
            cycle_start = (date.today() - timedelta(days=365 * cycle_years)).isoformat()
        records = self._credit_records.get(attorney_id, [])
        if cycle_start:
            records = [r for r in records if r["at"] >= cycle_start]
        total_hours = round(sum(r["credit_hours_earned"] for r in records), 4)
        ethics_hours = round(sum(r["credit_hours_earned"] for r in records if r["is_ethics"]), 4)
        required = rules.get("credit_hours_required_per_cycle", 0)
        ethics_required = rules.get("ethics_required", 0)
        # Self-study cap (NY only, simplified)
        self_study_cap_hours = None
        if rules.get("self_study_cap_pct"):
            self_study_cap_hours = round(required * rules["self_study_cap_pct"] / 100, 2)
        return {
            "attorney_id": attorney_id,
            "jurisdiction": jurisdiction,
            "jurisdiction_name": rules["name"],
            "cycle_years": cycle_years,
            "cycle_start": cycle_start,
            "credit_hours_earned": total_hours,
            "credit_hours_required": required,
            "credit_hours_remaining": max(0, round(required - total_hours, 4)),
            "ethics_hours_earned": ethics_hours,
            "ethics_hours_required": ethics_required,
            "ethics_hours_remaining": max(0, round(ethics_required - ethics_hours, 4)),
            "self_study_cap_hours": self_study_cap_hours,
            "compliance_status": "compliant" if total_hours >= required and ethics_hours >= ethics_required else "in_progress",
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": (
                "Estimated CLE credit accumulation. Each state bar has the final say "
                "on credit eligibility. Verom partners with accredited CLE providers "
                "for formal credit reporting; this summary is for tracking purposes only."
            ),
        }

    # ---------- network analytics ----------
    def network_health(self) -> dict:
        threads = list(self._threads.values())
        last_30 = [t for t in threads if t["created_at"] >= (date.today() - timedelta(days=30)).isoformat()]
        activities = [a for a in self._activities if a["at"] >= (date.today() - timedelta(days=30)).isoformat()]
        all_comments = [c for thread_comments in self._comments.values() for c in thread_comments]
        recent_comments = [c for c in all_comments if c["posted_at"] >= (date.today() - timedelta(days=30)).isoformat()]
        unique_authors = {t.get("author_user_id") for t in threads if t.get("author_user_id")}
        return {
            "thread_count": len(threads),
            "comment_count": len(all_comments),
            "threads_last_30_days": len(last_30),
            "comments_last_30_days": len(recent_comments),
            "unique_authors": len(unique_authors),
            "cle_activities_last_30_days": len(activities),
            "median_response_time_hours": _median_response_time(threads, self._comments),
            "computed_at": datetime.utcnow().isoformat(),
        }


def _median_response_time(threads: list, comments_by_thread: dict) -> float | None:
    """Median time-to-first-comment across threads with comments."""
    response_times = []
    for thread in threads:
        comments = comments_by_thread.get(thread["id"], [])
        if not comments:
            continue
        try:
            opened = datetime.fromisoformat(thread["created_at"])
            first_comment = min(datetime.fromisoformat(c["posted_at"]) for c in comments)
            hours = (first_comment - opened).total_seconds() / 3600
            response_times.append(hours)
        except ValueError:
            continue
    if not response_times:
        return None
    return round(statistics.median(response_times), 2)
