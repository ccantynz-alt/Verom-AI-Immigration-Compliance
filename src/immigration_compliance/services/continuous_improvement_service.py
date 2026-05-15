"""Continuous Improvement Service — the Zero Idle Time flywheel.

Core principle: Claude is never idle. When there is no user task in-flight, the
flywheel pulls work from the improvement queue — scanning competitors, auditing
for bugs, drafting upgrade proposals, and advancing the product at least once a
day. Every tick of the flywheel emits a ledger entry so we can audit exactly
what advanced, when, and why.

The flywheel has four wheels:
  1. SCAN   — gather signals (competitor moves, dependency releases, bug reports)
  2. IDEATE — convert signals into concrete improvement ideas
  3. BUILD  — dequeue an idea and mark it in-progress for implementation
  4. SHIP   — record the advancement in the daily ledger and close the loop

Legal note: the flywheel only surfaces public, non-privileged signals. Client
data, case files, and attorney-client communications are NEVER fed into the
learning loop. A compliance gate on every signal ingestion enforces this.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any


class FlywheelStage(str, Enum):
    SCAN = "scan"
    IDEATE = "ideate"
    BUILD = "build"
    SHIP = "ship"


class ImprovementStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SHIPPED = "shipped"
    DEFERRED = "deferred"
    REJECTED = "rejected"


class ImprovementPriority(str, Enum):
    P0_BROKEN = "p0_broken"          # something is broken — drop everything
    P1_COMPETITIVE = "p1_competitive"  # competitor feature gap
    P2_UPGRADE = "p2_upgrade"          # dependency / tooling upgrade
    P3_POLISH = "p3_polish"            # quality of life / polish
    P4_IDEA = "p4_idea"                # speculative / submit to human


class SignalSource(str, Enum):
    COMPETITOR = "competitor"
    DEPENDENCY = "dependency"
    BUG_REPORT = "bug_report"
    REGULATORY = "regulatory"
    INTERNAL_AUDIT = "internal_audit"
    USER_FEEDBACK = "user_feedback"
    GATE_TEST = "gate_test"


# Signals that MUST be rejected before they enter the flywheel — privileged data
# never trains or drives the improvement loop.
_PROHIBITED_SIGNAL_KEYS = {
    "client_data",
    "attorney_client_communication",
    "case_file",
    "privileged",
    "pii_record",
}


@dataclass
class Signal:
    id: str
    source: SignalSource
    summary: str
    payload: dict[str, Any]
    captured_at: str
    relevance: float  # 0..1


@dataclass
class ImprovementIdea:
    id: str
    title: str
    rationale: str
    priority: ImprovementPriority
    status: ImprovementStatus
    origin_signal_id: str | None
    created_at: str
    updated_at: str
    shipped_at: str | None = None
    tags: list[str] = field(default_factory=list)
    estimated_impact: str = ""
    implementation_hint: str = ""


@dataclass
class AdvancementRecord:
    id: str
    date: str
    title: str
    description: str
    improvement_id: str | None
    commit_sha: str | None
    shipped_by: str  # "claude" or user handle


class ContinuousImprovementService:
    """The flywheel engine — zero idle time, daily advancement mandate."""

    DAILY_ADVANCEMENT_TARGET = 1  # at least one advancement per day, per CLAUDE.md

    def __init__(self) -> None:
        self._signals: dict[str, Signal] = {}
        self._ideas: dict[str, ImprovementIdea] = {}
        self._ledger: dict[str, AdvancementRecord] = {}
        self._flywheel_started_at = datetime.utcnow().isoformat()
        self._tick_count = 0

    # ------------------------------------------------------------------
    # Signal ingestion (SCAN wheel)
    # ------------------------------------------------------------------
    def ingest_signal(
        self,
        source: SignalSource,
        summary: str,
        payload: dict[str, Any] | None = None,
        relevance: float = 0.5,
    ) -> Signal:
        """Accept a new signal for the flywheel. Privileged data is rejected."""
        payload = payload or {}
        self._assert_no_privileged_data(payload)
        relevance = max(0.0, min(1.0, relevance))
        sig = Signal(
            id=str(uuid.uuid4()),
            source=source,
            summary=summary,
            payload=payload,
            captured_at=datetime.utcnow().isoformat(),
            relevance=relevance,
        )
        self._signals[sig.id] = sig
        return sig

    def list_signals(self, source: SignalSource | None = None) -> list[Signal]:
        out = list(self._signals.values())
        if source is not None:
            out = [s for s in out if s.source == source]
        return sorted(out, key=lambda s: s.captured_at, reverse=True)

    @staticmethod
    def _assert_no_privileged_data(payload: dict[str, Any]) -> None:
        for key in payload.keys():
            if key.lower() in _PROHIBITED_SIGNAL_KEYS:
                raise ValueError(
                    f"Prohibited signal key '{key}' — privileged data cannot "
                    "enter the improvement flywheel."
                )

    # ------------------------------------------------------------------
    # Ideation (IDEATE wheel)
    # ------------------------------------------------------------------
    def propose_improvement(
        self,
        title: str,
        rationale: str,
        priority: ImprovementPriority = ImprovementPriority.P3_POLISH,
        origin_signal_id: str | None = None,
        tags: list[str] | None = None,
        estimated_impact: str = "",
        implementation_hint: str = "",
    ) -> ImprovementIdea:
        """Queue a concrete improvement idea."""
        if origin_signal_id and origin_signal_id not in self._signals:
            raise ValueError("origin_signal_id refers to an unknown signal")
        now = datetime.utcnow().isoformat()
        idea = ImprovementIdea(
            id=str(uuid.uuid4()),
            title=title,
            rationale=rationale,
            priority=priority,
            status=ImprovementStatus.QUEUED,
            origin_signal_id=origin_signal_id,
            created_at=now,
            updated_at=now,
            tags=list(tags or []),
            estimated_impact=estimated_impact,
            implementation_hint=implementation_hint,
        )
        self._ideas[idea.id] = idea
        return idea

    def list_queue(
        self,
        status: ImprovementStatus | None = None,
        priority: ImprovementPriority | None = None,
    ) -> list[ImprovementIdea]:
        out = list(self._ideas.values())
        if status is not None:
            out = [i for i in out if i.status == status]
        if priority is not None:
            out = [i for i in out if i.priority == priority]
        # Highest priority first, then oldest first (fifo within tier)
        order = [
            ImprovementPriority.P0_BROKEN,
            ImprovementPriority.P1_COMPETITIVE,
            ImprovementPriority.P2_UPGRADE,
            ImprovementPriority.P3_POLISH,
            ImprovementPriority.P4_IDEA,
        ]
        return sorted(out, key=lambda i: (order.index(i.priority), i.created_at))

    def next_task(self) -> ImprovementIdea | None:
        """Pull the next highest-priority queued idea. Zero Idle Time entry point."""
        queued = [i for i in self._ideas.values() if i.status == ImprovementStatus.QUEUED]
        if not queued:
            return None
        order = [
            ImprovementPriority.P0_BROKEN,
            ImprovementPriority.P1_COMPETITIVE,
            ImprovementPriority.P2_UPGRADE,
            ImprovementPriority.P3_POLISH,
            ImprovementPriority.P4_IDEA,
        ]
        queued.sort(key=lambda i: (order.index(i.priority), i.created_at))
        idea = queued[0]
        idea.status = ImprovementStatus.IN_PROGRESS
        idea.updated_at = datetime.utcnow().isoformat()
        return idea

    def defer(self, idea_id: str, reason: str = "") -> ImprovementIdea:
        idea = self._require(idea_id)
        idea.status = ImprovementStatus.DEFERRED
        idea.updated_at = datetime.utcnow().isoformat()
        if reason:
            idea.tags.append(f"deferred:{reason}")
        return idea

    def reject(self, idea_id: str, reason: str = "") -> ImprovementIdea:
        idea = self._require(idea_id)
        idea.status = ImprovementStatus.REJECTED
        idea.updated_at = datetime.utcnow().isoformat()
        if reason:
            idea.tags.append(f"rejected:{reason}")
        return idea

    # ------------------------------------------------------------------
    # Shipping (SHIP wheel) + Daily Advancement Ledger
    # ------------------------------------------------------------------
    def record_advancement(
        self,
        title: str,
        description: str,
        improvement_id: str | None = None,
        commit_sha: str | None = None,
        shipped_by: str = "claude",
    ) -> AdvancementRecord:
        """Mark an improvement as shipped and log it to the daily ledger."""
        if improvement_id is not None:
            idea = self._require(improvement_id)
            idea.status = ImprovementStatus.SHIPPED
            idea.shipped_at = datetime.utcnow().isoformat()
            idea.updated_at = idea.shipped_at
        rec = AdvancementRecord(
            id=str(uuid.uuid4()),
            date=date.today().isoformat(),
            title=title,
            description=description,
            improvement_id=improvement_id,
            commit_sha=commit_sha,
            shipped_by=shipped_by,
        )
        self._ledger[rec.id] = rec
        return rec

    def ledger_for(self, on_date: date | None = None) -> list[AdvancementRecord]:
        target = (on_date or date.today()).isoformat()
        return [r for r in self._ledger.values() if r.date == target]

    def ledger_range(self, start: date, end: date) -> list[AdvancementRecord]:
        s, e = start.isoformat(), end.isoformat()
        return sorted(
            [r for r in self._ledger.values() if s <= r.date <= e],
            key=lambda r: r.date,
        )

    def daily_mandate_status(self, on_date: date | None = None) -> dict[str, Any]:
        """Report whether the daily advancement mandate is satisfied."""
        target_date = on_date or date.today()
        shipped_today = self.ledger_for(target_date)
        met = len(shipped_today) >= self.DAILY_ADVANCEMENT_TARGET
        return {
            "date": target_date.isoformat(),
            "target": self.DAILY_ADVANCEMENT_TARGET,
            "shipped_count": len(shipped_today),
            "mandate_met": met,
            "shipped_titles": [r.title for r in shipped_today],
        }

    def streak(self) -> int:
        """Consecutive-day streak of meeting the daily advancement mandate."""
        if not self._ledger:
            return 0
        today = date.today()
        streak = 0
        for delta in range(0, 365):
            day = today - timedelta(days=delta)
            if self.daily_mandate_status(day)["mandate_met"]:
                streak += 1
            else:
                # Allow today to be 0 and not break the streak yet
                if delta == 0:
                    continue
                break
        return streak

    # ------------------------------------------------------------------
    # Flywheel tick — executed whenever Claude would otherwise be idle.
    # ------------------------------------------------------------------
    def tick(self) -> dict[str, Any]:
        """Run one flywheel cycle. Returns a summary of what was advanced.

        The tick is deterministic and side-effect-free beyond the service state:
        it surfaces the next queued idea and reports mandate status. Actual
        implementation of the idea is done by Claude (or a human) — this method
        just ensures no second of idle time goes unaccounted for.
        """
        self._tick_count += 1
        next_item = self.next_task()
        return {
            "tick": self._tick_count,
            "at": datetime.utcnow().isoformat(),
            "picked_up": None if next_item is None else {
                "id": next_item.id,
                "title": next_item.title,
                "priority": next_item.priority.value,
            },
            "queue_depth": sum(
                1 for i in self._ideas.values()
                if i.status == ImprovementStatus.QUEUED
            ),
            "mandate_today": self.daily_mandate_status(),
            "streak_days": self.streak(),
        }

    def flywheel_state(self) -> dict[str, Any]:
        counts: dict[str, int] = {s.value: 0 for s in ImprovementStatus}
        for idea in self._ideas.values():
            counts[idea.status.value] += 1
        return {
            "started_at": self._flywheel_started_at,
            "ticks": self._tick_count,
            "signals": len(self._signals),
            "ideas_total": len(self._ideas),
            "ideas_by_status": counts,
            "advancements_total": len(self._ledger),
            "mandate_today": self.daily_mandate_status(),
            "streak_days": self.streak(),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require(self, idea_id: str) -> ImprovementIdea:
        idea = self._ideas.get(idea_id)
        if idea is None:
            raise ValueError(f"Unknown improvement id: {idea_id}")
        return idea
