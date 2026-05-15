"""Tests for storage binding — service state survives across instances."""

import os
import tempfile

from immigration_compliance.services.persistent_store_service import PersistentStore
from immigration_compliance.services.storage_binding import bind_storage, SERVICE_STATE_ATTRS
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService
from immigration_compliance.services.intake_engine_service import IntakeEngineService
from immigration_compliance.services.document_intake_service import DocumentIntakeService
from immigration_compliance.services.form_population_service import FormPopulationService
from immigration_compliance.services.conflict_check_service import ConflictCheckService
from immigration_compliance.services.onboarding_service import OnboardingService
from immigration_compliance.services.family_bundle_service import FamilyBundleService
from immigration_compliance.services.client_chatbot_service import ClientChatbotService
from immigration_compliance.services.regulatory_impact_service import RegulatoryImpactService
from immigration_compliance.services.migration_importer_service import MigrationImporterService
from immigration_compliance.services.petition_letter_service import PetitionLetterService
from immigration_compliance.services.rfe_response_service import RFEResponseService
from immigration_compliance.services.calendar_sync_service import CalendarSyncService


def _new_db():
    return tempfile.mktemp(suffix=".db")


def test_service_attrs_registry_covers_all_services():
    expected = {
        "CaseWorkspaceService", "IntakeEngineService", "DocumentIntakeService",
        "FormPopulationService", "ConflictCheckService", "OnboardingService",
        "FamilyBundleService", "ClientChatbotService", "PacketAssemblyService",
        "RegulatoryImpactService", "MigrationImporterService", "PetitionLetterService",
        "RFEResponseService", "AttorneyMatchService", "CalendarSyncService",
    }
    assert expected <= set(SERVICE_STATE_ATTRS.keys())


def test_case_workspace_state_persists_across_instances():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        cw = CaseWorkspaceService()
        saver = bind_storage(cw, store)
        ws = cw.create_workspace("user-1", "H-1B", "US")
        cw.add_deadline(ws["id"], "Test deadline", "2027-01-01")
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        cw2 = CaseWorkspaceService()
        bind_storage(cw2, store2)
        restored = cw2.list_workspaces()
        assert len(restored) == 1
        deadlines = cw2.list_deadlines(restored[0]["id"])
        assert len(deadlines) == 1
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_intake_engine_persists_sessions():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        ie = IntakeEngineService()
        saver = bind_storage(ie, store)
        sess = ie.start_session("user-1", "H-1B")
        ie.submit_answers(sess["id"], {"has_bachelors_or_higher": True})
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        ie2 = IntakeEngineService()
        bind_storage(ie2, store2)
        restored = ie2.get_session(sess["id"])
        assert restored is not None
        assert restored["answers"]["has_bachelors_or_higher"] is True
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_document_intake_persists_uploads():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        di = DocumentIntakeService()
        saver = bind_storage(di, store)
        doc = di.upload("user-1", "sess-1", "passport.pdf", size_bytes=500_000, resolution_dpi=300)
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        di2 = DocumentIntakeService()
        bind_storage(di2, store2)
        restored = di2.get_document(doc["id"])
        assert restored is not None
        assert restored["filename"] == "passport.pdf"
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_form_population_persists_records_and_provenance():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        fp = FormPopulationService()
        saver = bind_storage(fp, store)
        rec = fp.populate("I-129", "user-1", intake_answers={"petitioner_name": "Acme"}, extracted_documents=[])
        fp.update_field(rec["id"], "petitioner_legal_name", "Better Name")
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        fp2 = FormPopulationService()
        bind_storage(fp2, store2)
        restored = fp2.get_record(rec["id"])
        assert restored is not None
        assert restored["form_id"] == "I-129"
        # Provenance survived
        prov = fp2.get_provenance(record_id=rec["id"])
        assert any(p["kind"] == "manual_override" for p in prov)
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_conflict_check_persists_across_instances():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        cc = ConflictCheckService()
        saver = bind_storage(cc, store)
        cc.register_case({"id": "c-1", "attorney_id": "atty-1", "applicant_name": "John Smith"})
        cc.check_new_case({"applicant_name": "John Smith"}, attorney_id="atty-1")
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        cc2 = ConflictCheckService()
        bind_storage(cc2, store2)
        cases = cc2.list_cases()
        assert len(cases) == 1
        log = cc2.get_check_log()
        assert len(log) == 1
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_onboarding_session_persists():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        ob = OnboardingService()
        saver = bind_storage(ob, store)
        s = ob.start_applicant_onboarding("user-1")
        ob.submit_step(s["id"], "goal_selection", {"family": "work"})
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        ob2 = OnboardingService()
        bind_storage(ob2, store2)
        restored = ob2.get_session(s["id"])
        assert restored is not None
        assert restored["progress_pct"] > 0
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_chatbot_conversations_persist():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        # Workspace setup (no persistence on the workspace for this test)
        cw = CaseWorkspaceService()
        ws = cw.create_workspace("user-1", "H-1B", "US")
        cw.record_filing(ws["id"], "WAC123", "2026-08-01")

        bot = ClientChatbotService(case_workspace=cw)
        saver = bind_storage(bot, store)
        c = bot.get_or_create_conversation(ws["id"], "user-1")
        bot.ask(c["id"], "where is my case?")
        saver.flush()
        store.close()

        store2 = PersistentStore(db_path=db)
        bot2 = ClientChatbotService(case_workspace=cw)  # same in-memory workspace
        bind_storage(bot2, store2)
        msgs = bot2.get_messages(c["id"])
        # Should at least have welcome + user + bot replies
        assert len(msgs) >= 3
        store2.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_unbound_service_returns_none_from_bind():
    """Services not in the registry get a no-op binding (returns None)."""
    class CustomService:
        def __init__(self):
            self._foo = {}

    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        result = bind_storage(CustomService(), store)
        assert result is None
        store.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_bind_storage_does_not_break_returns():
    """Wrapped methods must still return their original results."""
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        cw = CaseWorkspaceService()
        bind_storage(cw, store)
        ws = cw.create_workspace("user-1", "H-1B", "US")
        # The return must still be the workspace dict
        assert ws is not None
        assert "id" in ws and ws["visa_type"] == "H-1B"
        store.close()
    finally:
        try: os.unlink(db)
        except OSError: pass


def test_multiple_services_share_one_store():
    db = _new_db()
    try:
        store = PersistentStore(db_path=db)
        cw = CaseWorkspaceService()
        ie = IntakeEngineService()
        sa = bind_storage(cw, store)
        sb = bind_storage(ie, store)
        cw.create_workspace("user-1", "H-1B", "US")
        ie.start_session("user-1", "H-1B")
        sa.flush(); sb.flush()
        ns = store.list_namespaces()
        names = {n["namespace"] for n in ns}
        assert {"case_workspace", "intake_engine"} <= names
        store.close()
    finally:
        try: os.unlink(db)
        except OSError: pass
