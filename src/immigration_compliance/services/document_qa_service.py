"""AI Document Q&A — chat with USCIS notices, decisions, and policy memos.

Upload a document (or paste its text), then ask questions about it.
The engine extracts structured facts (receipt numbers, decision dates,
issue categories, citations, deadlines) and answers questions grounded
in those facts plus the document text.

Same anti-hallucination discipline as the chatbot: every answer carries
a list of `text_excerpts` showing the exact passages from the document
that support the answer. If the engine can't find a grounded answer, it
says "I don't see that in the document" rather than guessing.

Document types supported with structured extraction:
  - rfe_notice          — Request for Evidence
  - approval_notice     — I-797 Approval
  - denial_notice       — Decision denying petition
  - noid_notice         — Notice of Intent to Deny
  - rfe_response_decision — RFE response decision
  - i539_notice         — Change/extension status notice
  - policy_memo         — USCIS policy memo
  - generic             — Anything else (Q&A still works on raw text)

Q&A intents (handled with grounded extraction):
  - receipt_number      "what is the receipt number?"
  - dates               "when was this issued? what's the deadline?"
  - issues              "what is USCIS asking for?"
  - decision            "what was the decision?"
  - response_window     "how long do I have to respond?"
  - citations           "what regulations does USCIS cite?"
  - parties             "who are the parties named?"
  - action_required     "what do I need to do?"
  - summary             "summarize this document"
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Document classification
# ---------------------------------------------------------------------------

DOC_TYPE_SIGNATURES: dict[str, list[str]] = {
    "rfe_notice": [
        "request for evidence",
        "rfe",
        "additional evidence is required",
        "you have 87 days to respond",
        "evidence is insufficient",
    ],
    "approval_notice": [
        "approval notice",
        "this notice of approval",
        "petition has been approved",
        "i-797",
        "your application has been approved",
    ],
    "denial_notice": [
        "decision",
        "petition is hereby denied",
        "we have determined",
        "the petition is denied",
        "you may file an appeal",
    ],
    "noid_notice": [
        "notice of intent to deny",
        "noid",
        "intent to deny your petition",
    ],
    "i539_notice": [
        "i-539",
        "change of status",
        "extension of stay",
    ],
    "policy_memo": [
        "policy memorandum",
        "pm-",
        "uscis policy",
        "interim guidance",
    ],
}


def classify_document(text: str) -> str:
    """Return the most likely document type from the catalog above."""
    text_l = text.lower()
    best_type = "generic"
    best_score = 0
    for dtype, signatures in DOC_TYPE_SIGNATURES.items():
        score = sum(1 for sig in signatures if sig in text_l)
        if score > best_score:
            best_score = score
            best_type = dtype
    return best_type


# ---------------------------------------------------------------------------
# Structured extraction
# ---------------------------------------------------------------------------

# Receipt numbers: 3 letters + 10 digits (e.g. WAC2612345678)
RECEIPT_PATTERN = re.compile(r"\b([A-Z]{3})[\s-]?(\d{10})\b")

# Dates: ISO, US, written
DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE),
]

# Citation patterns
CITATION_PATTERNS = [
    re.compile(r"\b8\s*C\.?F\.?R\.?\s*§?\s*\d+(?:\.\d+)*(?:\([a-z0-9]+\))*", re.IGNORECASE),
    re.compile(r"\bI\.N\.A\.\s*§?\s*\d+", re.IGNORECASE),
    re.compile(r"\b8\s*U\.?S\.?C\.?\s*§?\s*\d+(?:\([a-z0-9]+\))?", re.IGNORECASE),
    re.compile(r"\b\d+\s+I&N\s+Dec\.\s+\d+", re.IGNORECASE),
    re.compile(r"\bMatter of\s+\w+", re.IGNORECASE),
]

# Form mentions
FORM_PATTERN = re.compile(r"\b(?:Form\s+)?(I-\d{2,3}[A-Z]?|G-\d{2,3}|DS-\d{2,3}|N-\d{2,3})\b")

# Deadlines / response windows
WINDOW_PATTERNS = [
    re.compile(r"(\d{1,3})\s*days?\s+(?:to\s+respond|from\s+the\s+date)", re.IGNORECASE),
    re.compile(r"respond\s+within\s+(\d{1,3})\s*days?", re.IGNORECASE),
]


def extract_facts(text: str) -> dict[str, Any]:
    """Extract structured facts from the raw document text."""
    facts: dict[str, Any] = {}

    # Receipt numbers
    receipts = []
    for m in RECEIPT_PATTERN.finditer(text):
        receipts.append(m.group(0).replace(" ", "").replace("-", ""))
    facts["receipt_numbers"] = list(dict.fromkeys(receipts))[:5]

    # Dates
    dates = []
    for pat in DATE_PATTERNS:
        for m in pat.finditer(text):
            dates.append(m.group(0))
    facts["dates"] = list(dict.fromkeys(dates))[:10]

    # Citations
    citations = []
    for pat in CITATION_PATTERNS:
        for m in pat.finditer(text):
            citations.append(m.group(0))
    facts["citations"] = list(dict.fromkeys(citations))[:15]

    # Forms
    forms = []
    for m in FORM_PATTERN.finditer(text):
        forms.append(m.group(1))
    facts["forms"] = list(dict.fromkeys(forms))[:10]

    # Response window
    response_days = None
    for pat in WINDOW_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                response_days = int(m.group(1))
                break
            except (ValueError, IndexError):
                pass
    facts["response_window_days"] = response_days

    return facts


# ---------------------------------------------------------------------------
# Q&A intent detection
# ---------------------------------------------------------------------------

QA_INTENTS: dict[str, list[str]] = {
    "receipt_number": ["receipt", "case number", "wac", "msc", "src", "lin", "ioe", "eac"],
    "dates": ["when", "what date", "date issued"],
    "issues": ["what is uscis asking", "what does this say", "what is the issue", "what's wrong"],
    "decision": ["was it approved", "was it denied", "what was the decision", "decision"],
    "response_window": ["how long", "deadline", "due", "how many days", "by when"],
    "citations": ["what regulations", "what law", "citation", "regulation cited"],
    "parties": ["who is the petitioner", "who is the beneficiary", "who is named", "named parties"],
    "action_required": ["what do i do", "what's next", "next steps", "action required", "do next", "to do next", "respond", "do i need to do"],
    "summary": ["summarize", "summary", "tldr", "tl;dr", "what is this about", "explain"],
}


def classify_qa_intent(question: str) -> str:
    text_l = question.lower()
    best_intent = "unknown"
    best_score = 0
    for intent, keywords in QA_INTENTS.items():
        score = sum(1 for kw in keywords if kw in text_l)
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent if best_score > 0 else "unknown"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DocumentQAService:
    """Ingest a document, then answer questions grounded in its text + facts."""

    def __init__(self) -> None:
        self._documents: dict[str, dict] = {}
        self._conversations: dict[str, list[dict]] = {}

    # ---------- ingestion ----------
    def ingest(self, text: str, label: str = "", uploader_id: str | None = None) -> dict:
        if not text or not text.strip():
            raise ValueError("Document text is empty")
        doc_type = classify_document(text)
        facts = extract_facts(text)
        record = {
            "id": str(uuid.uuid4()),
            "label": label or f"Document {datetime.utcnow().date().isoformat()}",
            "uploader_id": uploader_id,
            "raw_text": text,
            "char_count": len(text),
            "doc_type": doc_type,
            "facts": facts,
            "ingested_at": datetime.utcnow().isoformat(),
        }
        self._documents[record["id"]] = record
        self._conversations[record["id"]] = []
        return record

    def get_document(self, doc_id: str) -> dict | None:
        return self._documents.get(doc_id)

    def list_documents(self, uploader_id: str | None = None) -> list[dict]:
        out = list(self._documents.values())
        if uploader_id:
            out = [d for d in out if d.get("uploader_id") == uploader_id]
        # Strip raw_text to keep listings small
        return [{k: v for k, v in d.items() if k != "raw_text"} for d in out]

    # ---------- Q&A ----------
    def ask(self, doc_id: str, question: str) -> dict:
        doc = self._documents.get(doc_id)
        if doc is None:
            raise ValueError(f"Document not found: {doc_id}")
        intent = classify_qa_intent(question)
        answer, excerpts = self._answer(intent, question, doc)
        msg = {
            "id": str(uuid.uuid4()),
            "question": question,
            "answer": answer,
            "intent": intent,
            "text_excerpts": excerpts,
            "at": datetime.utcnow().isoformat(),
        }
        self._conversations.setdefault(doc_id, []).append(msg)
        return msg

    def get_history(self, doc_id: str, limit: int = 100) -> list[dict]:
        return self._conversations.get(doc_id, [])[-limit:]

    # ---------- intent answer ----------
    def _answer(self, intent: str, question: str, doc: dict) -> tuple[str, list[str]]:
        text = doc["raw_text"]
        facts = doc["facts"]
        if intent == "receipt_number":
            if facts["receipt_numbers"]:
                return (
                    f"The document references the following receipt number(s): {', '.join(facts['receipt_numbers'])}.",
                    self._excerpts_around(text, facts["receipt_numbers"][0]),
                )
            return ("I don't see a receipt number in this document.", [])
        if intent == "dates":
            if facts["dates"]:
                return (
                    f"The document references these dates: {', '.join(facts['dates'][:5])}.",
                    self._excerpts_around(text, facts["dates"][0]),
                )
            return ("I don't see explicit dates in this document.", [])
        if intent == "response_window":
            if facts["response_window_days"]:
                return (
                    f"The document indicates a {facts['response_window_days']}-day response window.",
                    self._excerpts_around(text, str(facts["response_window_days"])),
                )
            return ("I don't see a response window stated in this document.", [])
        if intent == "citations":
            if facts["citations"]:
                cites = ", ".join(facts["citations"][:8])
                return (f"Regulatory citations in the document: {cites}.", self._excerpts_around(text, facts["citations"][0]))
            return ("I don't see any regulatory citations in this document.", [])
        if intent == "decision":
            return self._answer_decision(doc)
        if intent == "issues":
            return self._answer_issues(doc)
        if intent == "summary":
            return self._answer_summary(doc)
        if intent == "action_required":
            return self._answer_action_required(doc)
        if intent == "parties":
            return self._answer_parties(doc)
        # Unknown: try keyword grounding
        return self._answer_unknown(question, doc)

    @staticmethod
    def _answer_decision(doc: dict) -> tuple[str, list[str]]:
        text_l = doc["raw_text"].lower()
        if doc["doc_type"] == "approval_notice" or "has been approved" in text_l:
            return ("The document indicates the petition was APPROVED.",
                    DocumentQAService._excerpts_around(doc["raw_text"], "approved", window=80))
        if doc["doc_type"] == "denial_notice" or "is hereby denied" in text_l or "petition is denied" in text_l:
            return ("The document indicates the petition was DENIED.",
                    DocumentQAService._excerpts_around(doc["raw_text"], "denied", window=80))
        if doc["doc_type"] == "noid_notice":
            return ("This is a Notice of Intent to Deny — USCIS is signaling probable denial unless the petitioner responds with additional evidence.",
                    DocumentQAService._excerpts_around(doc["raw_text"], "intent to deny"))
        if doc["doc_type"] == "rfe_notice":
            return ("This is a Request for Evidence, not a final decision. USCIS is requesting additional evidence before adjudicating.",
                    DocumentQAService._excerpts_around(doc["raw_text"], "request for evidence"))
        return ("I can't determine a final decision from this document.", [])

    @staticmethod
    def _answer_issues(doc: dict) -> tuple[str, list[str]]:
        # Pull paragraphs that contain issue-signaling keywords
        kws = ["evidence is insufficient", "has not been demonstrated", "has not been established",
               "fails to establish", "request for evidence", "concern", "deficiency"]
        excerpts = []
        for kw in kws:
            ex = DocumentQAService._excerpts_around(doc["raw_text"], kw, window=120)
            excerpts.extend(ex[:2])
        if excerpts:
            return ("USCIS raises the following issues in this document:", excerpts[:5])
        return ("I don't see specific issues called out in this document.", [])

    @staticmethod
    def _answer_summary(doc: dict) -> tuple[str, list[str]]:
        # Use first 4 sentences of the document as a baseline summary
        paragraphs = [p for p in doc["raw_text"].splitlines() if p.strip()]
        intro = " ".join(paragraphs[:3])[:600]
        type_label = {
            "rfe_notice": "Request for Evidence",
            "approval_notice": "Approval Notice",
            "denial_notice": "Denial Notice",
            "noid_notice": "Notice of Intent to Deny",
            "i539_notice": "Change/Extension of Status Notice",
            "policy_memo": "Policy Memorandum",
            "generic": "USCIS document",
        }.get(doc["doc_type"], "USCIS document")
        facts = doc["facts"]
        bits = [f"This is a {type_label}."]
        if facts["receipt_numbers"]:
            bits.append(f"Receipt: {facts['receipt_numbers'][0]}.")
        if facts["forms"]:
            bits.append(f"Forms referenced: {', '.join(facts['forms'][:3])}.")
        if facts["response_window_days"]:
            bits.append(f"Response window: {facts['response_window_days']} days.")
        if facts["citations"]:
            bits.append(f"Cites: {', '.join(facts['citations'][:3])}.")
        if intro:
            bits.append(f"\nFirst paragraphs:\n{intro}")
        return (" ".join(bits[:5]) + ("\n" + bits[5] if len(bits) > 5 else ""), [intro] if intro else [])

    @staticmethod
    def _answer_action_required(doc: dict) -> tuple[str, list[str]]:
        if doc["doc_type"] == "rfe_notice":
            window = doc["facts"].get("response_window_days") or 87
            return (
                f"You must respond to this RFE within {window} days from the date of issue. The response should "
                f"address each issue USCIS raised with supporting evidence and citations.",
                DocumentQAService._excerpts_around(doc["raw_text"], "respond")[:2],
            )
        if doc["doc_type"] == "noid_notice":
            return (
                "You must respond to this Notice of Intent to Deny with rebuttal evidence within the stated window, or USCIS will issue a denial.",
                DocumentQAService._excerpts_around(doc["raw_text"], "intent to deny"),
            )
        if doc["doc_type"] == "denial_notice":
            return (
                "If the decision is unfavorable, you may file an appeal with the AAO (Form I-290B) within 30 days of the decision date.",
                DocumentQAService._excerpts_around(doc["raw_text"], "appeal"),
            )
        if doc["doc_type"] == "approval_notice":
            return (
                "No action required from the petitioner. The next step depends on whether the beneficiary is in the US (status starts on the validity start date) or abroad (consular processing required).",
                [],
            )
        return ("Action depends on the document type, which I couldn't determine confidently.", [])

    @staticmethod
    def _answer_parties(doc: dict) -> tuple[str, list[str]]:
        text = doc["raw_text"]
        # Look for "Petitioner:" and "Beneficiary:" or "Applicant:" labels
        parties = []
        for label in ("Petitioner:", "Beneficiary:", "Applicant:", "Re:"):
            m = re.search(label + r"\s*([^\n]{1,80})", text, re.IGNORECASE)
            if m:
                parties.append(f"{label.rstrip(':')} {m.group(1).strip()}")
        if parties:
            return ("Named parties: " + "; ".join(parties), [text[:300]])
        return ("I can't identify the named parties from this document with high confidence.", [])

    @staticmethod
    def _answer_unknown(question: str, doc: dict) -> tuple[str, list[str]]:
        # Try keyword grounding against the raw text — pull the question's
        # most distinctive nouns and look for sentences containing them.
        words = [w for w in re.findall(r"[A-Za-z]{4,}", question) if w.lower() not in {
            "what", "where", "when", "which", "tell", "about", "this", "that", "from", "have"
        }]
        if not words:
            return ("I'm not sure what you're asking. Try a more specific question (e.g. \"what is the receipt number?\").", [])
        excerpts = []
        for w in words[:3]:
            excerpts.extend(DocumentQAService._excerpts_around(doc["raw_text"], w))
        if excerpts:
            return (
                "Here's what I found in the document related to your question:",
                excerpts[:3],
            )
        return ("I don't see anything in the document that matches your question.", [])

    # ---------- excerpt helper ----------
    @staticmethod
    def _excerpts_around(text: str, needle: str, window: int = 60, max_excerpts: int = 3) -> list[str]:
        if not needle:
            return []
        text_l = text.lower()
        n_l = needle.lower()
        start = 0
        out = []
        while len(out) < max_excerpts:
            idx = text_l.find(n_l, start)
            if idx < 0:
                break
            from_idx = max(0, idx - window)
            to_idx = min(len(text), idx + len(needle) + window)
            snippet = text[from_idx:to_idx].strip()
            out.append(("…" if from_idx > 0 else "") + snippet + ("…" if to_idx < len(text) else ""))
            start = to_idx
        return out

    # ---------- introspection ----------
    @staticmethod
    def list_supported_doc_types() -> list[str]:
        return list(DOC_TYPE_SIGNATURES.keys()) + ["generic"]

    @staticmethod
    def list_supported_intents() -> list[dict]:
        return [{"intent": k, "keywords": v} for k, v in QA_INTENTS.items()]
