"""Tests for the Document Management service (vault + versions + tags)."""

from immigration_compliance.services.document_management_service import (
    DocumentManagementService,
    CATEGORY_FOLDERS,
    SHARE_ROLES,
)


def test_folders_cover_immigration_categories():
    expected = {"identity", "education", "financial", "civil", "evidentiary"}
    assert expected <= set(CATEGORY_FOLDERS.keys())


def test_register_entry_creates_v1():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="Passport", category="identity",
                           version_filename="p.pdf")
    assert e["current_version"] == 1
    assert e["pinned_version"] == 1
    versions = svc.list_versions(e["id"])
    assert len(versions) == 1


def test_register_unknown_category_rejected():
    svc = DocumentManagementService()
    try:
        svc.register_entry(workspace_id="ws-1", title="X", category="invalid")
        assert False
    except ValueError:
        pass


def test_add_version_increments():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v1.pdf")
    v2 = svc.add_version(e["id"], filename="v2.pdf", comment="Updated")
    assert v2["version_number"] == 2
    assert svc.get_entry(e["id"])["current_version"] == 2


def test_pin_specific_version():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v1.pdf")
    svc.add_version(e["id"], filename="v2.pdf")
    svc.pin_version(e["id"], 1)
    assert svc.get_entry(e["id"])["pinned_version"] == 1
    pinned = svc.get_pinned_version(e["id"])
    assert pinned["filename"] == "v1.pdf"


def test_pin_invalid_version_rejected():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v1.pdf")
    try:
        svc.pin_version(e["id"], 99)
        assert False
    except ValueError:
        pass


def test_add_remove_tag():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v1.pdf")
    svc.add_tag(e["id"], "priority")
    svc.add_tag(e["id"], "verified")
    assert "priority" in svc.get_entry(e["id"])["tags"]
    svc.remove_tag(e["id"], "priority")
    assert "priority" not in svc.get_entry(e["id"])["tags"]


def test_filter_by_tag():
    svc = DocumentManagementService()
    e1 = svc.register_entry(workspace_id="ws-1", title="A", category="identity",
                            version_filename="a.pdf", tags=["priority"])
    e2 = svc.register_entry(workspace_id="ws-1", title="B", category="financial",
                            version_filename="b.pdf", tags=["normal"])
    priority = svc.list_entries(workspace_id="ws-1", tag="priority")
    assert len(priority) == 1
    assert priority[0]["id"] == e1["id"]


def test_list_entries_by_folder():
    svc = DocumentManagementService()
    svc.register_entry(workspace_id="ws-1", title="A", category="identity", version_filename="a.pdf")
    svc.register_entry(workspace_id="ws-1", title="B", category="education", version_filename="b.pdf")
    folders = svc.list_entries_by_folder("ws-1")
    assert len(folders["01 - Identity"]) == 1
    assert len(folders["03 - Education + Credentials"]) == 1


def test_comments_visibility_filtering():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    svc.add_comment(e["id"], body="Internal note", author_id="atty-1", visibility="internal")
    svc.add_comment(e["id"], body="Client question", author_id="atty-1", visibility="client_visible")
    internal = svc.list_comments(e["id"], visibility="internal")
    client = svc.list_comments(e["id"], visibility="client_visible")
    assert len(internal) == 1
    assert len(client) == 1


def test_invalid_comment_visibility_rejected():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    try:
        svc.add_comment(e["id"], "X", author_id="u", visibility="public")
        assert False
    except ValueError:
        pass


def test_share_link_lifecycle():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    link = svc.create_share_link(e["id"], role="viewer", expires_in_days=14)
    assert link["role"] == "viewer"
    assert link["active"] is True
    found = svc.get_share_link(link["token"])
    assert found is not None
    svc.revoke_share_link(link["token"])
    assert svc.get_share_link(link["token"]) is None


def test_share_link_invalid_role_rejected():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    try:
        svc.create_share_link(e["id"], role="superuser")
        assert False
    except ValueError:
        pass


def test_archive_and_restore():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    svc.archive_entry(e["id"])
    assert svc.get_entry(e["id"])["active"] is False
    # By default, list_entries hides inactive
    assert len(svc.list_entries(workspace_id="ws-1")) == 0
    assert len(svc.list_entries(workspace_id="ws-1", include_inactive=True)) == 1
    svc.restore_entry(e["id"])
    assert svc.get_entry(e["id"])["active"] is True


def test_move_to_category():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    svc.move_to_category(e["id"], "evidentiary")
    refreshed = svc.get_entry(e["id"])
    assert refreshed["category"] == "evidentiary"
    assert "Evidence" in refreshed["folder_label"]


def test_activity_log_records_actions():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v.pdf")
    svc.add_tag(e["id"], "priority")
    svc.log_view(e["id"], actor_id="user-1")
    svc.log_download(e["id"], actor_id="user-1", version_number=1)
    log = svc.get_activity_log(entry_id=e["id"])
    actions = [a["action"] for a in log]
    assert "created" in actions
    assert "tagged" in actions
    assert "viewed" in actions
    assert "downloaded" in actions


def test_tags_in_use_counts():
    svc = DocumentManagementService()
    svc.register_entry(workspace_id="ws-1", title="A", category="identity", version_filename="a.pdf",
                       tags=["priority", "verified"])
    svc.register_entry(workspace_id="ws-1", title="B", category="education", version_filename="b.pdf",
                       tags=["priority"])
    tags = svc.list_tags_in_use(workspace_id="ws-1")
    tag_dict = {t["tag"]: t["count"] for t in tags}
    assert tag_dict["priority"] == 2
    assert tag_dict["verified"] == 1


def test_update_title():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="Old", category="identity", version_filename="v.pdf")
    svc.update_title(e["id"], "New Title")
    assert svc.get_entry(e["id"])["title"] == "New Title"


def test_share_roles_constant():
    assert set(SHARE_ROLES) == {"viewer", "commenter", "editor"}


def test_listing_entries_filters_by_category():
    svc = DocumentManagementService()
    svc.register_entry(workspace_id="ws-1", title="A", category="identity", version_filename="a.pdf")
    svc.register_entry(workspace_id="ws-1", title="B", category="financial", version_filename="b.pdf")
    identity = svc.list_entries(workspace_id="ws-1", category="identity")
    assert len(identity) == 1


def test_versions_preserve_history():
    svc = DocumentManagementService()
    e = svc.register_entry(workspace_id="ws-1", title="P", category="identity", version_filename="v1.pdf")
    svc.add_version(e["id"], filename="v2.pdf", comment="Update 1")
    svc.add_version(e["id"], filename="v3.pdf", comment="Update 2")
    versions = svc.list_versions(e["id"])
    assert len(versions) == 3
    # All versions retain their original filename
    assert versions[0]["filename"] == "v1.pdf"
    assert versions[1]["filename"] == "v2.pdf"
    assert versions[2]["filename"] == "v3.pdf"
