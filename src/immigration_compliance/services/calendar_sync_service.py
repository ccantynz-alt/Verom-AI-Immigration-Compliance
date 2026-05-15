"""Calendar Sync — turn workspace deadlines into real calendar events.

Three integration surfaces, in increasing fidelity:

  1. ICS FEED        — Subscribe URL per applicant (or per attorney) that
                       returns a live iCalendar feed. Works with Google
                       Calendar, Outlook, Apple Calendar, every calendar
                       client. No OAuth required.

  2. ICS SNAPSHOT    — One-shot download of an .ics file for a workspace
                       or set of workspaces.

  3. OAUTH PUSH      — Direct event creation in Google Calendar / Outlook.
                       Requires OAuth tokens; stubbed here behind a clean
                       dispatcher interface so the real OAuth wiring is a
                       drop-in later.

The ICS generator is hand-written (no external deps) so it stays portable
and deterministic. It produces RFC 5545 compliant calendars covering:
  - filing receipts (single all-day events)
  - filing-derived deadlines (auto-computed by CaseWorkspaceService)
  - RFE response deadlines
  - manual deadlines
  - status-change milestones (optional, off by default)

Subscription tokens are opaque random strings tied to the user/workspace
they grant access to. They can be rotated. They are NOT JWTs — calendar
clients don't refresh tokens, so a rotation invalidates an existing
subscription which is exactly the security model we want.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# RFC 5545 helpers
# ---------------------------------------------------------------------------

ICS_PRODID = "-//Verom AI Immigration Compliance//EN"
ICS_VERSION = "2.0"


def _ics_escape(text: str) -> str:
    """Escape commas, semicolons, and newlines per RFC 5545 §3.3.11."""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


def _ics_fold(line: str) -> str:
    """Fold lines longer than 75 octets per RFC 5545 §3.1."""
    if len(line) <= 75:
        return line
    out: list[str] = []
    while len(line) > 75:
        out.append(line[:75])
        line = " " + line[75:]
    out.append(line)
    return "\r\n".join(out)


def _ics_date(d: str | date) -> str:
    """Format a date as YYYYMMDD for VALUE=DATE properties."""
    if isinstance(d, date):
        return d.strftime("%Y%m%d")
    try:
        return date.fromisoformat(d).strftime("%Y%m%d")
    except (TypeError, ValueError):
        return datetime.utcnow().strftime("%Y%m%d")


def _ics_datetime_utc(dt: datetime | None = None) -> str:
    dt = dt or datetime.utcnow()
    return dt.strftime("%Y%m%dT%H%M%SZ")


def _ics_uid(*parts: str) -> str:
    """Stable UID derived from the parts so a re-render of the same event
    keeps the same UID (calendar clients dedup by UID)."""
    h = hashlib.sha1("|".join(parts).encode()).hexdigest()[:24]  # noqa: S324
    return f"{h}@verom.ai"


# ---------------------------------------------------------------------------
# Event spec
# ---------------------------------------------------------------------------

class IcsEvent:
    """Lightweight all-day event spec — keeps the generator data-driven."""

    __slots__ = ("uid", "summary", "description", "due_date", "categories", "url")

    def __init__(
        self,
        uid: str,
        summary: str,
        due_date: str,
        description: str = "",
        categories: Iterable[str] | None = None,
        url: str = "",
    ) -> None:
        self.uid = uid
        self.summary = summary
        self.description = description
        self.due_date = due_date
        self.categories = list(categories or [])
        self.url = url

    def render(self) -> list[str]:
        start = _ics_date(self.due_date)
        end_d = self._next_day(self.due_date)
        lines = [
            "BEGIN:VEVENT",
            _ics_fold(f"UID:{self.uid}"),
            _ics_fold(f"DTSTAMP:{_ics_datetime_utc()}"),
            _ics_fold(f"DTSTART;VALUE=DATE:{start}"),
            _ics_fold(f"DTEND;VALUE=DATE:{end_d}"),
            _ics_fold(f"SUMMARY:{_ics_escape(self.summary)}"),
        ]
        if self.description:
            lines.append(_ics_fold(f"DESCRIPTION:{_ics_escape(self.description)}"))
        if self.categories:
            lines.append(_ics_fold(f"CATEGORIES:{','.join(self.categories)}"))
        if self.url:
            lines.append(_ics_fold(f"URL:{self.url}"))
        # 24-hour and 7-day reminders for any due date
        lines.extend([
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "TRIGGER:-P1D",
            "END:VALARM",
            "BEGIN:VALARM",
            "ACTION:DISPLAY",
            "DESCRIPTION:Reminder",
            "TRIGGER:-P7D",
            "END:VALARM",
            "END:VEVENT",
        ])
        return lines

    @staticmethod
    def _next_day(d: str | date) -> str:
        try:
            base = date.fromisoformat(str(d))
        except (TypeError, ValueError):
            base = date.today()
        return (base + timedelta(days=1)).strftime("%Y%m%d")


def render_calendar(events: Iterable[IcsEvent], calendar_name: str = "Verom Immigration") -> str:
    body = [
        "BEGIN:VCALENDAR",
        f"PRODID:{ICS_PRODID}",
        f"VERSION:{ICS_VERSION}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        _ics_fold(f"X-WR-CALNAME:{_ics_escape(calendar_name)}"),
        "X-WR-TIMEZONE:UTC",
    ]
    for ev in events:
        body.extend(ev.render())
    body.append("END:VCALENDAR")
    return "\r\n".join(body) + "\r\n"


# ---------------------------------------------------------------------------
# Calendar Sync Service
# ---------------------------------------------------------------------------

PROVIDER_CHOICES = ("google", "outlook", "apple", "ics")


class CalendarSyncService:
    """Calendar sync orchestrator. Pulls deadlines from CaseWorkspaceService.

    Subscriptions: each user can mint multiple subscription tokens (e.g. one
    per device/calendar). Tokens grant read access to the user's calendar
    feed and can be rotated independently."""

    def __init__(self, case_workspace: Any | None = None, base_url: str = "") -> None:
        self._cases = case_workspace
        self._base_url = base_url.rstrip("/")
        self._subscriptions: dict[str, dict] = {}        # token → subscription record
        self._oauth_connections: dict[str, dict] = {}    # connection_id → connection record
        self._push_log: list[dict] = []

    # ---------- subscription tokens ----------
    def create_subscription(
        self,
        user_id: str,
        scope: str = "applicant",  # "applicant" | "attorney" | "workspace"
        workspace_id: str | None = None,
        label: str = "",
    ) -> dict:
        if scope not in ("applicant", "attorney", "workspace"):
            raise ValueError("Invalid scope")
        if scope == "workspace" and not workspace_id:
            raise ValueError("workspace_id required for workspace scope")
        token = secrets.token_urlsafe(32)
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "scope": scope,
            "workspace_id": workspace_id,
            "label": label or f"{scope} feed",
            "token": token,
            "created_at": datetime.utcnow().isoformat(),
            "rotated_from": None,
            "active": True,
            "feed_url": self._feed_url(token),
        }
        self._subscriptions[token] = record
        return record

    def list_subscriptions(self, user_id: str | None = None, active_only: bool = True) -> list[dict]:
        subs = list(self._subscriptions.values())
        if user_id:
            subs = [s for s in subs if s["user_id"] == user_id]
        if active_only:
            subs = [s for s in subs if s["active"]]
        return subs

    def get_subscription(self, token: str) -> dict | None:
        sub = self._subscriptions.get(token)
        if sub and sub["active"]:
            return sub
        return None

    def rotate_subscription(self, old_token: str) -> dict | None:
        old = self._subscriptions.get(old_token)
        if old is None:
            return None
        old["active"] = False
        new = self.create_subscription(
            user_id=old["user_id"],
            scope=old["scope"],
            workspace_id=old.get("workspace_id"),
            label=old["label"],
        )
        new["rotated_from"] = old["id"]
        return new

    def revoke_subscription(self, token: str) -> bool:
        sub = self._subscriptions.get(token)
        if sub is None:
            return False
        sub["active"] = False
        sub["revoked_at"] = datetime.utcnow().isoformat()
        return True

    def _feed_url(self, token: str) -> str:
        if self._base_url:
            return f"{self._base_url}/api/calendar/feed/{token}.ics"
        return f"/api/calendar/feed/{token}.ics"

    # ---------- ICS generation ----------
    def render_workspace_calendar(self, workspace: dict, deadlines: list[dict]) -> str:
        events = list(self._workspace_events(workspace, deadlines))
        cal_name = f"Verom · {workspace.get('label') or workspace.get('visa_type') or 'Case'}"
        return render_calendar(events, calendar_name=cal_name)

    def render_user_calendar(self, user_id: str, scope: str = "applicant") -> str:
        if not self._cases:
            return render_calendar([], calendar_name="Verom Immigration")
        if scope == "attorney":
            workspaces = self._cases.list_workspaces(attorney_id=user_id)
        else:
            workspaces = self._cases.list_workspaces(applicant_id=user_id)
        all_events: list[IcsEvent] = []
        for ws in workspaces:
            deadlines = self._cases.list_deadlines(ws["id"], include_completed=False)
            all_events.extend(self._workspace_events(ws, deadlines))
        cal_name = f"Verom Immigration · {scope}"
        return render_calendar(all_events, calendar_name=cal_name)

    def render_feed_for_token(self, token: str) -> str | None:
        sub = self.get_subscription(token)
        if sub is None:
            return None
        if sub["scope"] == "workspace":
            ws = self._cases.get_workspace(sub["workspace_id"]) if self._cases else None
            if ws is None:
                return render_calendar([], calendar_name="Verom Immigration")
            deadlines = self._cases.list_deadlines(sub["workspace_id"], include_completed=False)
            return self.render_workspace_calendar(ws, deadlines)
        return self.render_user_calendar(sub["user_id"], scope=sub["scope"])

    def _workspace_events(self, ws: dict, deadlines: list[dict]) -> Iterable[IcsEvent]:
        ws_label = ws.get("label") or f"{ws.get('visa_type', 'Case')} — {ws.get('id', '')[:6]}"
        # Filing event
        if ws.get("filed_date") and ws.get("filing_receipt_number"):
            yield IcsEvent(
                uid=_ics_uid("workspace", ws["id"], "filing", ws["filing_receipt_number"]),
                summary=f"Filed: {ws['filing_receipt_number']} — {ws_label}",
                description=(
                    f"Visa: {ws.get('visa_type')}\\n"
                    f"Country: {ws.get('country')}\\n"
                    f"Receipt: {ws['filing_receipt_number']}"
                ),
                due_date=ws["filed_date"],
                categories=["Verom", "Filing"],
                url=self._workspace_url(ws["id"]),
            )
        # Deadlines
        for d in deadlines:
            yield IcsEvent(
                uid=_ics_uid("deadline", ws["id"], d["id"]),
                summary=f"{d['label']} — {ws_label}",
                description=(
                    f"Case: {ws_label}\\n"
                    f"Kind: {d.get('kind', 'general')}\\n"
                    f"Source: {d.get('source', 'manual')}"
                ),
                due_date=d["due_date"],
                categories=["Verom", "Deadline", d.get("kind", "general").title()],
                url=self._workspace_url(ws["id"]),
            )

    def _workspace_url(self, ws_id: str) -> str:
        if self._base_url:
            return f"{self._base_url}/case?id={ws_id}"
        return f"/case?id={ws_id}"

    # ---------- OAuth push (stubbed, ready to wire) ----------
    def connect_provider(self, user_id: str, provider: str, oauth_payload: dict) -> dict:
        """Store an OAuth connection. Real implementation validates the token,
        fetches the user profile, and persists a refresh token. Here we record
        the metadata so the dispatcher knows where to push."""
        if provider not in PROVIDER_CHOICES:
            raise ValueError(f"Unknown provider: {provider}")
        connection_id = str(uuid.uuid4())
        record = {
            "id": connection_id,
            "user_id": user_id,
            "provider": provider,
            "external_account": oauth_payload.get("email") or oauth_payload.get("account") or "",
            "scopes": oauth_payload.get("scopes", []),
            "connected_at": datetime.utcnow().isoformat(),
            "active": True,
            "calendar_id": oauth_payload.get("calendar_id", "primary"),
        }
        self._oauth_connections[connection_id] = record
        return record

    def list_connections(self, user_id: str | None = None, provider: str | None = None) -> list[dict]:
        cs = list(self._oauth_connections.values())
        if user_id:
            cs = [c for c in cs if c["user_id"] == user_id]
        if provider:
            cs = [c for c in cs if c["provider"] == provider]
        return [c for c in cs if c["active"]]

    def disconnect(self, connection_id: str) -> bool:
        c = self._oauth_connections.get(connection_id)
        if c is None:
            return False
        c["active"] = False
        c["disconnected_at"] = datetime.utcnow().isoformat()
        return True

    def push_workspace_to_calendar(self, connection_id: str, workspace_id: str) -> dict:
        """Push all of a workspace's events to the connected calendar.

        Implementation note: this records *intent* in a push log. Real OAuth
        delivery happens in a downstream worker that consumes the push log,
        calls the provider's API, and updates `delivered_at`. Stubbing here
        keeps the service interface stable so the worker is a drop-in."""
        connection = self._oauth_connections.get(connection_id)
        if connection is None or not connection["active"]:
            raise ValueError("Connection not found or inactive")
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")
        ws = self._cases.get_workspace(workspace_id)
        if ws is None:
            raise ValueError("Workspace not found")
        deadlines = self._cases.list_deadlines(workspace_id, include_completed=False)
        events = list(self._workspace_events(ws, deadlines))
        push_id = str(uuid.uuid4())
        entry = {
            "id": push_id,
            "connection_id": connection_id,
            "provider": connection["provider"],
            "workspace_id": workspace_id,
            "event_count": len(events),
            "queued_at": datetime.utcnow().isoformat(),
            "status": "queued",
            "delivered_at": None,
        }
        self._push_log.append(entry)
        return entry

    def get_push_log(self, connection_id: str | None = None, limit: int = 100) -> list[dict]:
        log = self._push_log
        if connection_id:
            log = [e for e in log if e["connection_id"] == connection_id]
        return log[-limit:]

    @staticmethod
    def list_supported_providers() -> list[dict]:
        return [
            {"id": "google", "name": "Google Calendar", "auth": "oauth2", "scopes_required": ["https://www.googleapis.com/auth/calendar.events"]},
            {"id": "outlook", "name": "Microsoft Outlook", "auth": "oauth2", "scopes_required": ["Calendars.ReadWrite"]},
            {"id": "apple", "name": "Apple Calendar", "auth": "ics_subscribe", "notes": "Apple Calendar subscribes to ICS feeds — use the subscription URL."},
            {"id": "ics", "name": "Any calendar (ICS subscribe)", "auth": "ics_subscribe", "notes": "Universal ICS feed; works in every calendar app."},
        ]
