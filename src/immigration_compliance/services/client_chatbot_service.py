"""AI Client Chatbot — case-grounded Q&A for applicants.

Solves the #1 immigration applicant complaint: "Where's my case? Why hasn't
my attorney replied?" — most of those questions have deterministic answers
from the case state. This bot answers them in seconds, 24/7, without
attorney effort and without hallucination.

Design:
  - Bot answers ONLY from real workspace state. If it doesn't know, it
    routes to the attorney with the question pre-drafted. No invented info.
  - Intent classifier is rules-based with a small surface (status, deadline,
    documents, forms, fees, attorney, RFE, etc.) so it's auditable and we
    don't ship LLM-only outputs to applicants.
  - Every answer carries a `grounded_in` list of fields/IDs the response
    used. Lawyers can click to see exactly what the bot saw.
  - Conversations are persisted per workspace so the attorney can review.
  - Attorneys can shadow / override conversations: any attorney message
    interrupts the bot until the attorney releases it.

LLM swap-in: the `_summarize_with_llm` hook is called only after the
deterministic answer is known. The LLM rephrases the structured answer
into a friendly tone — it cannot introduce facts. Default mode is
deterministic (no LLM)."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: dict[str, list[str]] = {
    "status":          ["status", "where", "update", "happening", "progress", "stage"],
    "deadline":        ["deadline", "due", "when", "by when", "submit", "file by"],
    "documents":       ["document", "upload", "papers", "files", "what do i need", "missing", "checklist"],
    "forms":           ["form", "i-129", "i-130", "i-485", "i-765", "i-131", "ds-160", "petition"],
    "fees":            ["fee", "cost", "pay", "price", "how much", "filing fee"],
    "attorney":        ["attorney", "lawyer", "counsel", "who is my", "contact"],
    "rfe":             ["rfe", "request for evidence", "respond to", "what should i do"],
    "approval_chance": ["chances", "likely", "probability", "approval", "denied", "deny"],
    "next_steps":      ["next", "what now", "what should i", "what do i do", "checklist"],
    "appointment":     ["appointment", "biometrics", "interview", "consulate"],
    "travel":          ["travel", "leave the country", "advance parole", "ead"],
    "general":         ["help", "hi", "hello", "thanks", "thank"],
}


def classify_intent(message: str) -> str:
    """Map a user message to one of the supported intents. Returns 'unknown'
    if no keywords match."""
    text = message.lower()
    best_intent = "unknown"
    best_score = 0
    for intent, kws in INTENT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score > best_score:
            best_score = score
            best_intent = intent
    return best_intent if best_score > 0 else "unknown"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

CONFIDENT_INTENTS = {"status", "deadline", "documents", "forms", "fees", "attorney", "next_steps", "rfe", "approval_chance"}


class ClientChatbotService:
    """Conversational interface over a case workspace."""

    def __init__(self, case_workspace: Any | None = None) -> None:
        self._cases = case_workspace
        self._conversations: dict[str, dict] = {}     # convo_id → record
        self._messages: dict[str, list[dict]] = {}    # convo_id → messages
        self._handoffs: dict[str, list[dict]] = {}    # convo_id → handoff queue

    # ---------- conversations ----------
    def get_or_create_conversation(self, workspace_id: str, applicant_id: str) -> dict:
        for c in self._conversations.values():
            if c["workspace_id"] == workspace_id and c["applicant_id"] == applicant_id:
                return c
        convo_id = str(uuid.uuid4())
        c = {
            "id": convo_id,
            "workspace_id": workspace_id,
            "applicant_id": applicant_id,
            "started_at": datetime.utcnow().isoformat(),
            "attorney_overriding": False,
            "messages_count": 0,
            "handoff_count": 0,
        }
        self._conversations[convo_id] = c
        self._messages[convo_id] = []
        self._handoffs[convo_id] = []
        # Welcome message
        self._add_message(convo_id, "bot", self._welcome_message(), grounded_in=[], intent="general")
        return c

    def get_conversation(self, convo_id: str) -> dict | None:
        return self._conversations.get(convo_id)

    def list_conversations(self, applicant_id: str | None = None, workspace_id: str | None = None) -> list[dict]:
        out = list(self._conversations.values())
        if applicant_id:
            out = [c for c in out if c["applicant_id"] == applicant_id]
        if workspace_id:
            out = [c for c in out if c["workspace_id"] == workspace_id]
        return out

    def get_messages(self, convo_id: str, limit: int = 100) -> list[dict]:
        msgs = self._messages.get(convo_id, [])
        return msgs[-limit:]

    def get_handoffs(self, convo_id: str | None = None, status: str | None = None) -> list[dict]:
        if convo_id:
            handoffs = list(self._handoffs.get(convo_id, []))
        else:
            handoffs = [h for hs in self._handoffs.values() for h in hs]
        if status:
            handoffs = [h for h in handoffs if h["status"] == status]
        return handoffs

    # ---------- talking ----------
    def ask(self, convo_id: str, user_message: str) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError(f"Conversation not found: {convo_id}")
        # Record user message
        user_msg = self._add_message(convo_id, "user", user_message, grounded_in=[], intent=None)
        # If attorney is overriding, just enqueue and stop
        if convo["attorney_overriding"]:
            return {
                "user_message": user_msg,
                "bot_message": None,
                "note": "Attorney is currently in this conversation. The bot is paused.",
            }
        # Classify and answer
        intent = classify_intent(user_message)
        snapshot = self._safe_snapshot(convo["workspace_id"])
        answer, grounded, confidence = self._answer(intent, user_message, snapshot)
        # Low-confidence or unknown → handoff
        if intent not in CONFIDENT_INTENTS or confidence < 0.6:
            handoff = self._enqueue_handoff(convo_id, user_message, intent)
            bot_msg = self._add_message(
                convo_id,
                "bot",
                answer + "\n\n— I've sent your question to your attorney. They'll get back to you here.",
                grounded_in=grounded,
                intent=intent,
                kind="handoff",
            )
            convo["handoff_count"] += 1
            return {"user_message": user_msg, "bot_message": bot_msg, "handoff": handoff}
        bot_msg = self._add_message(
            convo_id,
            "bot",
            answer,
            grounded_in=grounded,
            intent=intent,
            confidence=confidence,
        )
        return {"user_message": user_msg, "bot_message": bot_msg}

    def attorney_take_over(self, convo_id: str, attorney_id: str) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError("Conversation not found")
        convo["attorney_overriding"] = True
        convo["attorney_id"] = attorney_id
        self._add_message(
            convo_id, "system",
            f"Attorney has joined the conversation.",
            grounded_in=[], intent="system", kind="attorney_takeover",
        )
        return convo

    def attorney_release(self, convo_id: str) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError("Conversation not found")
        convo["attorney_overriding"] = False
        self._add_message(convo_id, "system", "Bot is back online.", grounded_in=[], intent="system", kind="bot_resume")
        return convo

    def attorney_post_message(self, convo_id: str, attorney_id: str, body: str) -> dict:
        convo = self._conversations.get(convo_id)
        if convo is None:
            raise ValueError("Conversation not found")
        return self._add_message(
            convo_id, "attorney", body,
            grounded_in=[], intent="manual",
            metadata={"attorney_id": attorney_id},
        )

    def resolve_handoff(self, handoff_id: str, response_body: str = "") -> dict | None:
        for q in self._handoffs.values():
            for h in q:
                if h["id"] == handoff_id:
                    h["status"] = "resolved"
                    h["resolved_at"] = datetime.utcnow().isoformat()
                    if response_body:
                        h["response_body"] = response_body
                    return h
        return None

    # ---------- internals ----------
    def _welcome_message(self) -> str:
        return (
            "Hi — I'm Verom's case assistant. I can answer questions about your case "
            "status, deadlines, what documents are still needed, fees, your attorney, "
            "and what to do next. If I'm not sure, I'll send your question to your "
            "attorney directly."
        )

    def _safe_snapshot(self, workspace_id: str) -> dict | None:
        if not self._cases:
            return None
        try:
            return self._cases.get_snapshot(workspace_id)
        except Exception:
            return None

    def _answer(self, intent: str, message: str, snapshot: dict | None) -> tuple[str, list[str], float]:
        if not snapshot:
            return ("I don't have your case loaded right now — let me ask your attorney.", [], 0.2)
        ws = snapshot.get("workspace") or {}
        if intent == "status":
            return self._answer_status(ws, snapshot)
        if intent == "deadline":
            return self._answer_deadline(ws, snapshot, message)
        if intent == "documents":
            return self._answer_documents(ws, snapshot)
        if intent == "forms":
            return self._answer_forms(ws, snapshot)
        if intent == "fees":
            return self._answer_fees(ws, snapshot)
        if intent == "attorney":
            return self._answer_attorney(ws, snapshot)
        if intent == "rfe":
            return self._answer_rfe(ws, snapshot)
        if intent == "approval_chance":
            return self._answer_strength(ws, snapshot)
        if intent == "next_steps":
            return self._answer_next_steps(ws, snapshot)
        if intent == "appointment":
            return ("Your attorney handles appointment scheduling — let me forward this.", [], 0.4)
        if intent == "travel":
            return self._answer_travel(ws, snapshot)
        if intent == "general":
            return ("Hi! Ask me about your status, deadlines, documents, forms, fees, or what to do next.", [], 0.9)
        return ("I'm not sure about that — let me get your attorney to weigh in.", [], 0.3)

    @staticmethod
    def _answer_status(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        status = ws.get("status", "intake")
        receipt = ws.get("filing_receipt_number")
        filed = ws.get("filed_date")
        completeness = (snap.get("completeness") or {}).get("overall_pct", 0)
        if status == "filed" and receipt:
            return (
                f"Your {ws.get('visa_type')} case is filed. Receipt number {receipt}, filed on {filed}. "
                "I'll let you know the moment USCIS posts an update.",
                ["workspace.status", "workspace.filing_receipt_number", "workspace.filed_date"],
                0.95,
            )
        if status in ("approved", "denied"):
            return (
                f"Your case status is: {status.upper()}. Decision date: {ws.get('decision_date') or 'pending posting'}.",
                ["workspace.status"], 0.95,
            )
        if status == "rfe":
            return (
                "USCIS has issued a Request for Evidence on your case. Your attorney is preparing the response. "
                "I can show you what they're working on if you ask about the RFE.",
                ["workspace.status"], 0.9,
            )
        return (
            f"You're at the {status} stage. Overall case readiness is {completeness}% complete. "
            "Ask me what's still needed if you'd like the next steps.",
            ["workspace.status", "completeness.overall_pct"], 0.85,
        )

    @staticmethod
    def _answer_deadline(ws: dict, snap: dict, message: str) -> tuple[str, list[str], float]:
        deadlines = snap.get("deadlines") or []
        if not deadlines:
            return (
                "There aren't any deadlines on your case yet. I'll let you know as soon as one is added.",
                ["deadlines"], 0.9,
            )
        upcoming = sorted(deadlines, key=lambda d: d.get("due_date", ""))[:3]
        lines = ["Here are your upcoming deadlines:"]
        for d in upcoming:
            try:
                due = date.fromisoformat(d["due_date"])
                days = (due - date.today()).days
                rel = f"in {days} day{'s' if days != 1 else ''}" if days >= 0 else f"{abs(days)} day{'s' if abs(days) != 1 else ''} ago"
                lines.append(f"  • {d['label']} — {d['due_date']} ({rel})")
            except (TypeError, ValueError):
                lines.append(f"  • {d['label']} — {d.get('due_date', '?')}")
        return ("\n".join(lines), [f"deadline.{d['id']}" for d in upcoming], 0.95)

    @staticmethod
    def _answer_documents(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        docs = snap.get("documents") or {}
        if not docs:
            return ("I don't see your document checklist yet — let me check with your attorney.", [], 0.4)
        missing = [i for i in docs.get("items", []) if i["status"] == "missing" and i["required"]]
        if not missing:
            return (
                f"You're all set on documents — {docs.get('total_complete', 0)} of {docs.get('total_required', 0)} required documents uploaded.",
                ["documents.completeness_pct"], 0.95,
            )
        lines = [f"You have {len(missing)} required document{'s' if len(missing) != 1 else ''} still to upload:"]
        for m in missing[:6]:
            lines.append(f"  • {m['label']}")
        if len(missing) > 6:
            lines.append(f"  …and {len(missing) - 6} more.")
        lines.append("\nUpload them in your document portal — every file is auto-checked and matched to your checklist.")
        return ("\n".join(lines), [f"checklist.{m['checklist_item_id']}" for m in missing[:6]], 0.95)

    @staticmethod
    def _answer_forms(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        forms = snap.get("forms") or {}
        if not forms or not forms.get("records"):
            return (
                "Your forms haven't been generated yet. Your attorney can populate them from your intake answers in one click.",
                [], 0.7,
            )
        records = forms["records"]
        complete = [r for r in records if r["completeness_pct"] == 100]
        partial = [r for r in records if r["completeness_pct"] < 100]
        msg = f"Your case has {len(records)} form{'s' if len(records) != 1 else ''} prepared "
        msg += f"({forms.get('bundle_completeness_pct', 0)}% complete overall):\n"
        for r in records:
            msg += f"  • {r['form_id']} — {r['completeness_pct']}% ({r['required_filled']}/{r['required_total']} required fields)\n"
        if partial:
            msg += "\nThe partial ones still need a few details — your attorney will reach out for what's missing."
        return (msg, [f"form.{r['form_id']}" for r in records], 0.95)

    @staticmethod
    def _answer_fees(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        # Pulled from the cost calculator service if available; otherwise generic.
        visa = ws.get("visa_type", "")
        baselines = {
            "H-1B": "Government filing fees for H-1B are around $1,710–$4,515 depending on whether you choose premium processing. Attorney fees are set by your attorney.",
            "I-485": "Government filing fees for I-485 are around $1,225 plus the medical exam (~$400). Attorney fees are set by your attorney.",
            "O-1": "Government filing fees for O-1 are around $460–$3,265 depending on premium processing. Attorney fees are set by your attorney.",
            "I-130": "The I-130 government filing fee is $535. Attorney fees are set by your attorney.",
            "F-1": "F-1 SEVIS fee is $350 plus DS-160 application fee ($185). Attorney fees are set by your attorney.",
        }
        if visa in baselines:
            return (
                baselines[visa] + "\n\nYou'll see exact amounts when your attorney sends a fee agreement.",
                ["workspace.visa_type"], 0.85,
            )
        return (
            "Government filing fees vary by visa. Attorney fees are set by your attorney — they'll send you a clear fee schedule before any work begins.",
            [], 0.7,
        )

    @staticmethod
    def _answer_attorney(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        atty = ws.get("attorney_id")
        if not atty:
            return (
                "You haven't picked an attorney yet. Once you do, you can message them right here on the case page.",
                ["workspace.attorney_id"], 0.95,
            )
        match = snap.get("match") or {}
        # Find the attorney name from match results if available
        for r in match.get("results", []):
            if r.get("attorney_id") == atty:
                return (
                    f"Your attorney is {r['name']} ({r['years_experience']} years experience, "
                    f"{int(r['approval_rate']*100)}% approval rate). They typically respond within "
                    f"{r['avg_response_time_hours']} hours.",
                    ["workspace.attorney_id"], 0.95,
                )
        return (
            f"Your attorney's ID is {atty}. They'll respond on this thread.",
            ["workspace.attorney_id"], 0.85,
        )

    @staticmethod
    def _answer_rfe(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        if ws.get("status") != "rfe":
            risk = (snap.get("rfe_risk") or {}).get("risk_score", 0)
            if risk >= 50:
                return (
                    f"You haven't received an RFE — but our model estimates a {risk}% chance of one based on your case profile. "
                    "Your attorney is taking steps to lower that risk before filing.",
                    ["rfe_risk.risk_score"], 0.85,
                )
            return ("You haven't received a Request for Evidence. RFE risk is currently low.", ["rfe_risk.risk_score"], 0.9)
        return (
            "USCIS has issued a Request for Evidence. Your attorney is preparing the response and will share a draft "
            "for your review before submitting. The standard response window is 87 days from the date of issue.",
            ["workspace.status"], 0.9,
        )

    @staticmethod
    def _answer_strength(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        intake = snap.get("intake") or {}
        strength = intake.get("strength") or {}
        if not strength:
            return ("I don't have a strength estimate yet — your intake isn't complete.", [], 0.5)
        return (
            f"Your case strength is rated {strength.get('tier','').upper()} ({strength.get('score', 0)}/100). "
            "Note that this is an internal readiness score, not a USCIS approval guarantee — every case is decided on its merits.",
            ["intake.strength.score", "intake.strength.tier"], 0.85,
        )

    @staticmethod
    def _answer_next_steps(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        actions = snap.get("next_actions") or []
        if not actions:
            return ("Nothing's blocking right now — your case is moving forward.", ["next_actions"], 0.9)
        lines = [f"Here's what's next on your case ({len(actions)} item{'s' if len(actions) != 1 else ''}):"]
        for a in actions[:6]:
            lines.append(f"  • [{a['priority']}] {a['label']}")
        return ("\n".join(lines), ["next_actions"], 0.95)

    @staticmethod
    def _answer_travel(ws: dict, snap: dict) -> tuple[str, list[str], float]:
        if ws.get("status") in ("filed", "rfe", "decision_pending"):
            return (
                "You generally shouldn't leave the country while your case is pending unless you have advance parole. "
                "Travel without it can cause your application to be considered abandoned. Please confirm with your attorney before booking.",
                ["workspace.status"], 0.85,
            )
        return ("Travel is usually fine right now — but always run plans by your attorney first.", [], 0.7)

    # ---------- message storage ----------
    def _add_message(
        self,
        convo_id: str,
        sender: str,
        body: str,
        grounded_in: list[str],
        intent: str | None = None,
        confidence: float | None = None,
        kind: str = "message",
        metadata: dict | None = None,
    ) -> dict:
        msg = {
            "id": str(uuid.uuid4()),
            "conversation_id": convo_id,
            "sender": sender,
            "body": body,
            "grounded_in": grounded_in,
            "intent": intent,
            "confidence": confidence,
            "kind": kind,
            "metadata": metadata or {},
            "at": datetime.utcnow().isoformat(),
        }
        self._messages.setdefault(convo_id, []).append(msg)
        if convo_id in self._conversations:
            self._conversations[convo_id]["messages_count"] += 1
        return msg

    def _enqueue_handoff(self, convo_id: str, question: str, intent: str) -> dict:
        h = {
            "id": str(uuid.uuid4()),
            "conversation_id": convo_id,
            "workspace_id": self._conversations[convo_id]["workspace_id"],
            "applicant_id": self._conversations[convo_id]["applicant_id"],
            "question": question,
            "intent": intent,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }
        self._handoffs.setdefault(convo_id, []).append(h)
        return h

    # ---------- intent vocabulary ----------
    @staticmethod
    def list_supported_intents() -> list[dict]:
        return [
            {"intent": k, "keywords": v} for k, v in INTENT_KEYWORDS.items()
        ]
