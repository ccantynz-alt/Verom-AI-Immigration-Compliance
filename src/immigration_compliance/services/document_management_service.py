"""Document Management — case-organized vault with tags + version control.

Sits on top of DocumentIntakeService (raw uploads + classification) to add
the practice-management features attorneys actually need:

  - Per-case folder structure (auto-organized by category: identity,
    education, financial, civil, evidentiary, etc.)
  - Tags (free-form labels on documents)
  - Version control (each upload of the same document creates a new
    version while preserving the prior versions)
  - Pinning (mark canonical version)
  - Sharing (per-document share links + access control)
  - Activity log (who viewed / downloaded / commented when)

Designed to wrap the existing DocumentIntakeService — when a doc is
uploaded there, this service registers it as version 1 of a folder
entry and assigns the appropriate folder based on the classification.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Folder taxonomy
# ---------------------------------------------------------------------------

CATEGORY_FOLDERS: dict[str, str] = {
    "identity": "01 - Identity",
    "sponsor": "02 - Employer / Sponsor",
    "education": "03 - Education + Credentials",
    "financial": "04 - Financial",
    "civil": "05 - Civil Documents",
    "health": "06 - Medical",
    "background": "07 - Background Checks",
    "evidentiary": "08 - Evidence + Exhibits",
    "supporting": "09 - Supporting Materials",
    "internal": "10 - Internal / Attorney Work Product",
    "correspondence": "11 - Correspondence",
}


SHARE_ROLES = ("viewer", "commenter", "editor")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DocumentManagementService:
    """Folder-organized, versioned, tagged document vault per case."""

    def __init__(self, document_intake: Any | None = None) -> None:
        self._intake = document_intake
        self._entries: dict[str, dict] = {}              # entry_id → record (canonical entry per logical document)
        self._versions: dict[str, list[dict]] = {}       # entry_id → list of versions
        self._tags_index: dict[str, set[str]] = {}        # tag → set of entry_ids
        self._activity_log: list[dict] = []
        self._share_links: dict[str, dict] = {}           # token → record
        self._comments: dict[str, list[dict]] = {}        # entry_id → comments

    # ---------- introspection ----------
    @staticmethod
    def list_folders() -> list[dict]:
        return [
            {"category": k, "label": v}
            for k, v in CATEGORY_FOLDERS.items()
        ]

    # ---------- document entries ----------
    def register_entry(
        self,
        workspace_id: str,
        title: str,
        category: str,
        document_intake_id: str | None = None,
        version_filename: str = "",
        version_size_bytes: int = 0,
        version_uploader_id: str | None = None,
        tags: list[str] | None = None,
        notes: str = "",
    ) -> dict:
        """Register a logical document (canonical entry). Creates v1 of the
        version stack."""
        if category not in CATEGORY_FOLDERS:
            raise ValueError(f"Unknown category: {category}")
        entry_id = str(uuid.uuid4())
        record = {
            "id": entry_id, "workspace_id": workspace_id,
            "title": title, "category": category,
            "folder_label": CATEGORY_FOLDERS[category],
            "tags": list(tags or []),
            "notes": notes, "active": True,
            "current_version": 1,
            "pinned_version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._entries[entry_id] = record
        # Index tags
        for tag in record["tags"]:
            self._tags_index.setdefault(tag.lower(), set()).add(entry_id)
        # Create v1
        version = {
            "version_number": 1,
            "filename": version_filename,
            "size_bytes": version_size_bytes,
            "uploaded_by": version_uploader_id,
            "uploaded_at": datetime.utcnow().isoformat(),
            "document_intake_id": document_intake_id,
            "comment": "Initial version",
        }
        self._versions[entry_id] = [version]
        self._log_activity(entry_id, "created", actor_id=version_uploader_id, details=f"v1 — {version_filename}")
        return record

    def add_version(
        self,
        entry_id: str,
        filename: str,
        size_bytes: int = 0,
        uploader_id: str | None = None,
        comment: str = "",
        document_intake_id: str | None = None,
    ) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        next_version = entry["current_version"] + 1
        version = {
            "version_number": next_version,
            "filename": filename,
            "size_bytes": size_bytes,
            "uploaded_by": uploader_id,
            "uploaded_at": datetime.utcnow().isoformat(),
            "document_intake_id": document_intake_id,
            "comment": comment,
        }
        self._versions[entry_id].append(version)
        entry["current_version"] = next_version
        entry["updated_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "version_added", actor_id=uploader_id, details=f"v{next_version} — {filename}")
        return version

    def list_versions(self, entry_id: str) -> list[dict]:
        return list(self._versions.get(entry_id, []))

    def pin_version(self, entry_id: str, version_number: int, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        if version_number < 1 or version_number > entry["current_version"]:
            raise ValueError(f"Version {version_number} does not exist")
        entry["pinned_version"] = version_number
        entry["updated_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "pinned", actor_id=actor_id, details=f"v{version_number}")
        return entry

    def get_pinned_version(self, entry_id: str) -> dict | None:
        entry = self._entries.get(entry_id)
        if entry is None:
            return None
        versions = self._versions.get(entry_id, [])
        for v in versions:
            if v["version_number"] == entry["pinned_version"]:
                return v
        return None

    # ---------- entries listing ----------
    def get_entry(self, entry_id: str) -> dict | None:
        return self._entries.get(entry_id)

    def list_entries(
        self,
        workspace_id: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        include_inactive: bool = False,
    ) -> list[dict]:
        out = list(self._entries.values())
        if workspace_id:
            out = [e for e in out if e["workspace_id"] == workspace_id]
        if category:
            out = [e for e in out if e["category"] == category]
        if tag:
            ids_with_tag = self._tags_index.get(tag.lower(), set())
            out = [e for e in out if e["id"] in ids_with_tag]
        if not include_inactive:
            out = [e for e in out if e["active"]]
        return out

    def list_entries_by_folder(self, workspace_id: str) -> dict[str, list[dict]]:
        """Return entries grouped by folder for the file-tree UI."""
        entries = self.list_entries(workspace_id=workspace_id)
        by_folder: dict[str, list[dict]] = {label: [] for label in CATEGORY_FOLDERS.values()}
        for entry in entries:
            by_folder.setdefault(entry["folder_label"], []).append(entry)
        return by_folder

    # ---------- tags ----------
    def add_tag(self, entry_id: str, tag: str, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        if tag not in entry["tags"]:
            entry["tags"].append(tag)
            self._tags_index.setdefault(tag.lower(), set()).add(entry_id)
            self._log_activity(entry_id, "tagged", actor_id=actor_id, details=tag)
        return entry

    def remove_tag(self, entry_id: str, tag: str, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        if tag in entry["tags"]:
            entry["tags"].remove(tag)
            if tag.lower() in self._tags_index:
                self._tags_index[tag.lower()].discard(entry_id)
            self._log_activity(entry_id, "untagged", actor_id=actor_id, details=tag)
        return entry

    def list_tags_in_use(self, workspace_id: str | None = None) -> list[dict]:
        """Return distinct tags + counts."""
        counts: dict[str, int] = {}
        for entry in self._entries.values():
            if workspace_id and entry["workspace_id"] != workspace_id:
                continue
            if not entry["active"]:
                continue
            for tag in entry["tags"]:
                counts[tag] = counts.get(tag, 0) + 1
        return [{"tag": t, "count": c} for t, c in sorted(counts.items(), key=lambda x: -x[1])]

    # ---------- activity log ----------
    def _log_activity(
        self, entry_id: str, action: str,
        actor_id: str | None = None, details: str = "",
    ) -> dict:
        record = {
            "id": str(uuid.uuid4()),
            "entry_id": entry_id, "action": action,
            "actor_id": actor_id, "details": details,
            "at": datetime.utcnow().isoformat(),
        }
        self._activity_log.append(record)
        return record

    def log_view(self, entry_id: str, actor_id: str | None = None) -> dict:
        if entry_id not in self._entries:
            raise ValueError(f"Entry not found: {entry_id}")
        return self._log_activity(entry_id, "viewed", actor_id=actor_id)

    def log_download(self, entry_id: str, actor_id: str | None = None, version_number: int | None = None) -> dict:
        if entry_id not in self._entries:
            raise ValueError(f"Entry not found: {entry_id}")
        details = f"v{version_number}" if version_number else ""
        return self._log_activity(entry_id, "downloaded", actor_id=actor_id, details=details)

    def get_activity_log(self, entry_id: str | None = None, limit: int = 100) -> list[dict]:
        log = self._activity_log
        if entry_id:
            log = [a for a in log if a["entry_id"] == entry_id]
        return log[-limit:]

    # ---------- comments ----------
    def add_comment(
        self, entry_id: str, body: str, author_id: str,
        version_number: int | None = None, visibility: str = "internal",
    ) -> dict:
        if entry_id not in self._entries:
            raise ValueError(f"Entry not found: {entry_id}")
        if visibility not in ("internal", "client_visible"):
            raise ValueError("Visibility must be internal or client_visible")
        comment = {
            "id": str(uuid.uuid4()),
            "entry_id": entry_id, "author_id": author_id,
            "body": body, "version_number": version_number,
            "visibility": visibility,
            "at": datetime.utcnow().isoformat(),
        }
        self._comments.setdefault(entry_id, []).append(comment)
        self._log_activity(entry_id, "commented", actor_id=author_id, details=body[:80])
        return comment

    def list_comments(self, entry_id: str, visibility: str | None = None) -> list[dict]:
        out = list(self._comments.get(entry_id, []))
        if visibility:
            out = [c for c in out if c["visibility"] == visibility]
        return out

    # ---------- sharing ----------
    def create_share_link(
        self, entry_id: str, role: str = "viewer",
        expires_in_days: int = 7, created_by_user_id: str | None = None,
    ) -> dict:
        if entry_id not in self._entries:
            raise ValueError(f"Entry not found: {entry_id}")
        if role not in SHARE_ROLES:
            raise ValueError(f"Invalid share role: {role}")
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        record = {
            "token": token,
            "entry_id": entry_id, "role": role,
            "expires_at": expires_at,
            "created_by_user_id": created_by_user_id,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
            "url_path": f"/d/{token}",
            "view_count": 0,
        }
        self._share_links[token] = record
        self._log_activity(entry_id, "share_link_created", actor_id=created_by_user_id, details=f"role={role}")
        return record

    def get_share_link(self, token: str) -> dict | None:
        link = self._share_links.get(token)
        if link is None or not link["active"]:
            return None
        try:
            if datetime.fromisoformat(link["expires_at"]) < datetime.utcnow():
                return None
        except ValueError:
            return None
        return link

    def revoke_share_link(self, token: str) -> bool:
        link = self._share_links.get(token)
        if link is None:
            return False
        link["active"] = False
        link["revoked_at"] = datetime.utcnow().isoformat()
        return True

    def list_share_links(self, entry_id: str | None = None) -> list[dict]:
        out = list(self._share_links.values())
        if entry_id:
            out = [l for l in out if l["entry_id"] == entry_id]
        return out

    # ---------- entry operations ----------
    def archive_entry(self, entry_id: str, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        entry["active"] = False
        entry["archived_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "archived", actor_id=actor_id)
        return entry

    def restore_entry(self, entry_id: str, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        entry["active"] = True
        entry["restored_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "restored", actor_id=actor_id)
        return entry

    def update_title(self, entry_id: str, new_title: str, actor_id: str | None = None) -> dict:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        entry["title"] = new_title
        entry["updated_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "title_updated", actor_id=actor_id, details=new_title)
        return entry

    def move_to_category(self, entry_id: str, new_category: str, actor_id: str | None = None) -> dict:
        if new_category not in CATEGORY_FOLDERS:
            raise ValueError(f"Unknown category: {new_category}")
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ValueError(f"Entry not found: {entry_id}")
        entry["category"] = new_category
        entry["folder_label"] = CATEGORY_FOLDERS[new_category]
        entry["updated_at"] = datetime.utcnow().isoformat()
        self._log_activity(entry_id, "moved", actor_id=actor_id, details=new_category)
        return entry
