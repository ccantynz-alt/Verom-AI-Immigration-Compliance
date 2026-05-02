"""Tests for the AI Client Chatbot — case-grounded answers, intent classification, handoffs."""

from immigration_compliance.services.client_chatbot_service import (
    ClientChatbotService,
    classify_intent,
    INTENT_KEYWORDS,
    CONFIDENT_INTENTS,
)
from immigration_compliance.services.case_workspace_service import CaseWorkspaceService


def _make():
    cw = CaseWorkspaceService()
    bot = ClientChatbotService(case_workspace=cw)
    ws = cw.create_workspace("user-1", "H-1B", "US")
    return cw, bot, ws


def test_classify_intent_status():
    assert classify_intent("Where is my case at?") == "status"
    assert classify_intent("any update?") == "status"


def test_classify_intent_deadline():
    assert classify_intent("when is my deadline?") == "deadline"


def test_classify_intent_documents():
    assert classify_intent("what documents do I need to upload?") == "documents"


def test_classify_intent_fees():
    assert classify_intent("how much does this cost?") == "fees"


def test_classify_intent_unknown():
    assert classify_intent("the weather is nice") == "unknown"


def test_intent_keyword_keys_match_confident_intents():
    # Every confident intent must exist in the keyword map
    assert CONFIDENT_INTENTS <= set(INTENT_KEYWORDS.keys())


def test_get_or_create_returns_same_conversation():
    _, bot, ws = _make()
    c1 = bot.get_or_create_conversation(ws["id"], "user-1")
    c2 = bot.get_or_create_conversation(ws["id"], "user-1")
    assert c1["id"] == c2["id"]


def test_welcome_message_present():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    msgs = bot.get_messages(c["id"])
    assert len(msgs) == 1
    assert msgs[0]["sender"] == "bot"


def test_status_question_grounded_in_workspace():
    cw, bot, ws = _make()
    cw.record_filing(ws["id"], "WAC2612345678", "2026-11-01")
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    r = bot.ask(c["id"], "where is my case at?")
    assert r["bot_message"] is not None
    assert "WAC2612345678" in r["bot_message"]["body"]
    assert "workspace.filing_receipt_number" in r["bot_message"]["grounded_in"]


def test_deadline_question_lists_upcoming():
    cw, bot, ws = _make()
    cw.add_deadline(ws["id"], "RFE response", "2027-02-15", kind="rfe")
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    r = bot.ask(c["id"], "when is my deadline?")
    assert "RFE response" in r["bot_message"]["body"]


def test_unknown_intent_triggers_handoff():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    r = bot.ask(c["id"], "tell me about the weather forecast")
    assert "handoff" in r
    assert r["handoff"]["status"] == "pending"


def test_handoff_visible_in_pending_list():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    bot.ask(c["id"], "obscure question about something")
    pending = bot.get_handoffs(status="pending")
    assert len(pending) == 1


def test_attorney_take_over_pauses_bot():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    bot.attorney_take_over(c["id"], "atty-001")
    r = bot.ask(c["id"], "where is my case?")
    assert r["bot_message"] is None
    assert "paused" in r["note"].lower() or "Attorney is currently" in r["note"]


def test_attorney_release_resumes_bot():
    cw, bot, ws = _make()
    cw.record_filing(ws["id"], "WAC2612345678", "2026-11-01")
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    bot.attorney_take_over(c["id"], "atty-001")
    bot.attorney_release(c["id"])
    r = bot.ask(c["id"], "where is my case?")
    assert r["bot_message"] is not None


def test_attorney_message_logged():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    bot.attorney_take_over(c["id"], "atty-001")
    msg = bot.attorney_post_message(c["id"], "atty-001", "I'll review your case tomorrow morning.")
    assert msg["sender"] == "attorney"
    assert msg["metadata"]["attorney_id"] == "atty-001"


def test_resolve_handoff_marks_resolved():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    bot.ask(c["id"], "totally unrelated thing")
    pending = bot.get_handoffs(status="pending")
    h_id = pending[0]["id"]
    bot.resolve_handoff(h_id, "Thanks for asking!")
    resolved = bot.get_handoffs(status="resolved")
    assert any(r["id"] == h_id for r in resolved)


def test_attorney_question_with_assigned_attorney():
    cw, bot, ws = _make()
    cw.assign_attorney(ws["id"], "atty-001", "Jennifer Park")
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    r = bot.ask(c["id"], "who is my attorney?")
    # Without match data we still provide the attorney_id
    assert "atty-001" in r["bot_message"]["body"] or "Jennifer Park" in r["bot_message"]["body"]


def test_documents_intent_returns_low_confidence_when_no_snapshot_documents():
    _, bot, ws = _make()  # no documents wired
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    r = bot.ask(c["id"], "what documents do I need?")
    # No documents available → bot says it doesn't know yet
    assert r["bot_message"] is not None
    # Either confidence is low and triggered handoff, or it gave a partial answer
    assert "checklist" in r["bot_message"]["body"].lower() or "handoff" in r


def test_messages_count_increments():
    _, bot, ws = _make()
    c = bot.get_or_create_conversation(ws["id"], "user-1")
    initial = bot.get_conversation(c["id"])["messages_count"]
    bot.ask(c["id"], "where is my case?")
    final = bot.get_conversation(c["id"])["messages_count"]
    assert final >= initial + 2  # user + bot


def test_supported_intents_listing():
    intents = ClientChatbotService.list_supported_intents()
    intent_names = {i["intent"] for i in intents}
    assert "status" in intent_names and "deadline" in intent_names
