"""Tests for the AI Document Q&A service."""

from immigration_compliance.services.document_qa_service import (
    DocumentQAService,
    classify_document,
    classify_qa_intent,
    extract_facts,
    DOC_TYPE_SIGNATURES,
    QA_INTENTS,
)


SAMPLE_RFE = """USCIS REQUEST FOR EVIDENCE
Receipt: WAC2612345678
Date: November 1, 2026

Re: I-129 Petition
Petitioner: Acme Corp
Beneficiary: Wei Chen

Upon review of the petition, the evidence is insufficient to establish:

1. The position offered does not appear to be a specialty occupation under 8 C.F.R. § 214.2(h)(4)(iii)(A).
2. The employer-employee relationship has not been demonstrated.
3. The beneficiary's degree appears unrelated to the position.

You have 87 days from the date of this notice to respond.
"""

SAMPLE_APPROVAL = """I-797 NOTICE OF ACTION
Receipt: WAC2612345679
Date: October 15, 2026

Re: I-129 Petition for Acme Corp
Beneficiary: Wei Chen

Your application has been approved.

Validity: 2026-10-15 through 2029-10-14.
"""

SAMPLE_DENIAL = """USCIS DECISION
Receipt: WAC2611111111
Date: October 5, 2026

The petition is hereby denied.

You may file an appeal with the AAO within 30 days.
"""


def test_classify_rfe():
    assert classify_document(SAMPLE_RFE) == "rfe_notice"


def test_classify_approval():
    assert classify_document(SAMPLE_APPROVAL) == "approval_notice"


def test_classify_denial():
    assert classify_document(SAMPLE_DENIAL) == "denial_notice"


def test_classify_generic():
    assert classify_document("Just some random text without USCIS keywords.") == "generic"


def test_extract_receipt_numbers():
    facts = extract_facts(SAMPLE_RFE)
    assert "WAC2612345678" in facts["receipt_numbers"]


def test_extract_dates():
    facts = extract_facts(SAMPLE_RFE)
    assert any("November 1, 2026" in d for d in facts["dates"])


def test_extract_citations():
    facts = extract_facts(SAMPLE_RFE)
    assert any("8 C.F.R" in c for c in facts["citations"])


def test_extract_response_window():
    facts = extract_facts(SAMPLE_RFE)
    assert facts["response_window_days"] == 87


def test_extract_forms():
    facts = extract_facts(SAMPLE_RFE)
    assert "I-129" in facts["forms"]


def test_classify_qa_intent_receipt():
    assert classify_qa_intent("What is the receipt number?") == "receipt_number"


def test_classify_qa_intent_response_window():
    assert classify_qa_intent("How long do I have to respond?") == "response_window"


def test_classify_qa_intent_summary():
    assert classify_qa_intent("Summarize this document") == "summary"


def test_classify_qa_intent_action():
    assert classify_qa_intent("What do I need to do next?") == "action_required"


def test_classify_qa_intent_unknown():
    assert classify_qa_intent("What is the weather like?") == "unknown"


def test_ingest_creates_record():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE, label="test rfe", uploader_id="atty-1")
    assert doc["doc_type"] == "rfe_notice"
    assert doc["facts"]["receipt_numbers"]
    assert doc["uploader_id"] == "atty-1"


def test_ingest_empty_raises():
    svc = DocumentQAService()
    try:
        svc.ingest("")
        assert False
    except ValueError:
        pass


def test_ask_receipt_returns_grounded_answer():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "What is the receipt number?")
    assert "WAC2612345678" in r["answer"]
    assert len(r["text_excerpts"]) > 0


def test_ask_response_window():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "How many days do I have?")
    assert "87" in r["answer"]


def test_ask_decision_for_approval():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_APPROVAL)
    r = svc.ask(doc["id"], "Was it approved?")
    assert "APPROVED" in r["answer"]


def test_ask_decision_for_denial():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_DENIAL)
    r = svc.ask(doc["id"], "What was the decision?")
    assert "DENIED" in r["answer"]


def test_ask_decision_for_rfe_clarifies():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "What was the decision?")
    assert "not a final decision" in r["answer"].lower() or "request for evidence" in r["answer"].lower()


def test_ask_summary():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "Summarize this")
    assert "Request for Evidence" in r["answer"]


def test_ask_action_required_rfe():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "What do I need to do next?")
    assert "respond" in r["answer"].lower()


def test_ask_action_required_denial():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_DENIAL)
    r = svc.ask(doc["id"], "What's next?")
    assert "appeal" in r["answer"].lower()


def test_ask_parties():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    r = svc.ask(doc["id"], "Who is named in this document?")
    assert "Acme Corp" in r["answer"] or "Wei Chen" in r["answer"]


def test_ask_unknown_document():
    svc = DocumentQAService()
    try:
        svc.ask("not-a-doc-id", "anything")
        assert False
    except ValueError:
        pass


def test_history_records_questions():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    svc.ask(doc["id"], "Receipt number?")
    svc.ask(doc["id"], "When was this issued?")
    history = svc.get_history(doc["id"])
    assert len(history) == 2


def test_list_documents_filters_by_uploader():
    svc = DocumentQAService()
    svc.ingest(SAMPLE_RFE, uploader_id="user-1")
    svc.ingest(SAMPLE_APPROVAL, uploader_id="user-2")
    user_1 = svc.list_documents(uploader_id="user-1")
    assert len(user_1) == 1
    # raw_text stripped from listings
    assert "raw_text" not in user_1[0]


def test_get_document_returns_full_record():
    svc = DocumentQAService()
    doc = svc.ingest(SAMPLE_RFE)
    full = svc.get_document(doc["id"])
    assert "raw_text" in full
    assert full["raw_text"] == SAMPLE_RFE


def test_supported_doc_types_listed():
    types = DocumentQAService.list_supported_doc_types()
    assert "rfe_notice" in types
    assert "approval_notice" in types
    assert "generic" in types


def test_supported_intents_listed():
    intents = DocumentQAService.list_supported_intents()
    intent_ids = {i["intent"] for i in intents}
    assert "receipt_number" in intent_ids
    assert "summary" in intent_ids
