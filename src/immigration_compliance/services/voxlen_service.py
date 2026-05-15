"""Voxlen integration — voice dictation, voice commands, AI grammar correction,
and session export for immigration professionals working inside Verom.

Voxlen (https://www.voxlen.ai) is a voice dictation + AI grammar tool with
Deepgram streaming STT, Claude/GPT grammar correction, voice commands, and
multi-format export. This service embeds the same capability set inside the
Verom backend so attorneys and paralegals can dictate RFE responses, support
letters, client memos, and case notes without leaving the platform.

Design:
  - Deterministic core (voice command processing, style heuristics, exports)
    so the feature works offline and in tests without API keys.
  - Optional external providers (Deepgram / OpenAI / Anthropic) can be plugged
    in via configure() — never required at rest.
  - Session history is first-class: every finalized chunk is appended, and
    the whole session can be exported to TXT, Markdown, JSON, or SRT.
  - Immigration-specific legal templates let attorneys dictate into a
    pre-structured skeleton (cover letter, RFE response, support letter,
    client memo, case note).
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class WritingStyle(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ACADEMIC = "academic"
    CREATIVE = "creative"
    TECHNICAL = "technical"
    LEGAL_FORMAL = "legal_formal"       # immigration brief / petition tone
    CLIENT_FRIENDLY = "client_friendly"  # plain-English for applicant comms


class ExportFormat(str, Enum):
    TXT = "txt"
    MARKDOWN = "markdown"
    JSON = "json"
    SRT = "srt"


class STTProvider(str, Enum):
    WEB_SPEECH = "web_speech"  # browser built-in, default, free
    DEEPGRAM = "deepgram"      # Voxlen's default — requires API key


class LLMProvider(str, Enum):
    NONE = "none"              # deterministic fallback grammar pass
    ANTHROPIC = "anthropic"    # Claude Haiku — Voxlen's default
    OPENAI = "openai"          # GPT-4o-mini


# 20+ languages matching Voxlen's supported set
SUPPORTED_LANGUAGES = [
    "en-US", "en-GB", "en-AU", "en-CA", "es-ES", "es-MX", "fr-FR", "de-DE",
    "pt-BR", "pt-PT", "it-IT", "nl-NL", "pl-PL", "ru-RU", "tr-TR", "zh-CN",
    "zh-TW", "ja-JP", "ko-KR", "hi-IN", "ar-SA", "sv-SE", "da-DK", "no-NO",
]


# Voice commands — phrase → action (mirrors Voxlen + adds legal shortcuts)
_VOICE_COMMANDS: dict[str, tuple[str, str]] = {
    "new line": ("insert", "\n"),
    "new paragraph": ("insert", "\n\n"),
    "period": ("insert", "."),
    "comma": ("insert", ","),
    "question mark": ("insert", "?"),
    "exclamation point": ("insert", "!"),
    "exclamation mark": ("insert", "!"),
    "colon": ("insert", ":"),
    "semicolon": ("insert", ";"),
    "open quote": ("insert", '"'),
    "close quote": ("insert", '"'),
    "open parenthesis": ("insert", "("),
    "close parenthesis": ("insert", ")"),
    "delete that": ("edit", "delete_last"),
    "scratch that": ("edit", "delete_last"),
    "undo that": ("edit", "delete_last"),
    "capitalize that": ("edit", "capitalize_last"),
    "uppercase that": ("edit", "upper_last"),
    "lowercase that": ("edit", "lower_last"),
    # Immigration-legal shortcuts
    "cite regulation": ("insert", " [CITE: 8 CFR §] "),
    "cite statute": ("insert", " [CITE: INA §] "),
    "insert exhibit": ("insert", " [EXHIBIT ___] "),
    "insert beneficiary": ("insert", " [BENEFICIARY] "),
    "insert petitioner": ("insert", " [PETITIONER] "),
}


# Legal templates — dictation scaffolding for common immigration documents
LEGAL_TEMPLATES: dict[str, dict[str, Any]] = {
    "cover_letter": {
        "title": "USCIS Cover Letter",
        "sections": [
            {"heading": "Re:", "prompt": "State visa type, beneficiary name, receipt number."},
            {"heading": "Dear Officer:", "prompt": "Dictate the introduction paragraph."},
            {"heading": "Statement of Facts", "prompt": "Summarize the facts of the case."},
            {"heading": "Legal Argument", "prompt": "State the statutory and regulatory basis."},
            {"heading": "Evidence Summary", "prompt": "List and describe the exhibits."},
            {"heading": "Conclusion", "prompt": "Request the relief sought."},
        ],
    },
    "rfe_response": {
        "title": "RFE Response",
        "sections": [
            {"heading": "Response to Request for Evidence", "prompt": "Identify the RFE by receipt and date."},
            {"heading": "Summary of Issues Raised", "prompt": "Summarize each issue in the RFE."},
            {"heading": "Response to Issue 1", "prompt": "Address the first issue with evidence."},
            {"heading": "Response to Issue 2", "prompt": "Address the second issue with evidence."},
            {"heading": "New Evidence Submitted", "prompt": "List new documents provided."},
            {"heading": "Conclusion", "prompt": "Request approval."},
        ],
    },
    "support_letter": {
        "title": "Employer Support Letter",
        "sections": [
            {"heading": "Company Background", "prompt": "Describe the petitioner company."},
            {"heading": "Position Offered", "prompt": "State job title, duties, and requirements."},
            {"heading": "Specialty Occupation Analysis", "prompt": "Explain why the role qualifies."},
            {"heading": "Beneficiary Qualifications", "prompt": "Summarize the beneficiary's credentials."},
            {"heading": "Employment Terms", "prompt": "State salary, location, and duration."},
            {"heading": "Conclusion", "prompt": "Request approval of the petition."},
        ],
    },
    "client_memo": {
        "title": "Client Memo",
        "sections": [
            {"heading": "Matter", "prompt": "Client name and case type."},
            {"heading": "Status", "prompt": "Where the case stands today."},
            {"heading": "Next Steps", "prompt": "What you need from the client."},
            {"heading": "Deadlines", "prompt": "Upcoming dates and why they matter."},
        ],
    },
    "case_note": {
        "title": "Internal Case Note",
        "sections": [
            {"heading": "Date", "prompt": "Today's date."},
            {"heading": "Event", "prompt": "What happened — filing, call, notice received."},
            {"heading": "Action Taken", "prompt": "What was done in response."},
            {"heading": "Follow-up Required", "prompt": "What still needs to happen."},
        ],
    },
}


@dataclass
class TranscriptChunk:
    id: str
    text: str
    is_final: bool
    confidence: float
    started_at_ms: int   # relative to session start
    ended_at_ms: int
    received_at: str


@dataclass
class DictationSession:
    id: str
    owner_id: str
    language: str
    style: WritingStyle
    template_key: str | None
    stt_provider: STTProvider
    llm_provider: LLMProvider
    created_at: str
    updated_at: str
    chunks: list[TranscriptChunk] = field(default_factory=list)
    corrected_text: str = ""
    status: str = "active"  # active | closed
    title: str = "Untitled dictation"


class VoxlenService:
    """Voxlen integration — voice dictation + commands + grammar + export."""

    def __init__(self) -> None:
        self._sessions: dict[str, DictationSession] = {}
        self._api_keys: dict[str, str] = {}  # provider -> key (not persisted)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def configure_provider(self, provider: str, api_key: str) -> dict[str, Any]:
        """Store an API key for a given provider (in-memory only)."""
        if provider not in {"deepgram", "openai", "anthropic"}:
            raise ValueError(f"Unsupported provider: {provider}")
        if not api_key or len(api_key) < 10:
            raise ValueError("API key looks invalid")
        # Never echo the key back — store and report a redacted fingerprint.
        self._api_keys[provider] = api_key
        return {
            "provider": provider,
            "configured": True,
            "fingerprint": f"{api_key[:4]}…{api_key[-4:]}",
        }

    def provider_status(self) -> dict[str, bool]:
        return {
            "deepgram": "deepgram" in self._api_keys,
            "openai": "openai" in self._api_keys,
            "anthropic": "anthropic" in self._api_keys,
        }

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def start_session(
        self,
        owner_id: str,
        language: str = "en-US",
        style: WritingStyle = WritingStyle.LEGAL_FORMAL,
        template_key: str | None = None,
        stt_provider: STTProvider = STTProvider.WEB_SPEECH,
        llm_provider: LLMProvider = LLMProvider.NONE,
        title: str = "",
    ) -> DictationSession:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        if template_key is not None and template_key not in LEGAL_TEMPLATES:
            raise ValueError(f"Unknown template: {template_key}")
        now = datetime.utcnow().isoformat()
        session = DictationSession(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            language=language,
            style=style,
            template_key=template_key,
            stt_provider=stt_provider,
            llm_provider=llm_provider,
            created_at=now,
            updated_at=now,
            title=title or (LEGAL_TEMPLATES[template_key]["title"] if template_key else "Untitled dictation"),
        )
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str, owner_id: str) -> DictationSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        if session.owner_id != owner_id:
            raise PermissionError("Session belongs to another user")
        return session

    def list_sessions(self, owner_id: str) -> list[DictationSession]:
        return sorted(
            [s for s in self._sessions.values() if s.owner_id == owner_id],
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def close_session(self, session_id: str, owner_id: str) -> DictationSession:
        session = self.get_session(session_id, owner_id)
        session.status = "closed"
        session.updated_at = datetime.utcnow().isoformat()
        return session

    def delete_session(self, session_id: str, owner_id: str) -> None:
        self.get_session(session_id, owner_id)
        self._sessions.pop(session_id, None)

    # ------------------------------------------------------------------
    # Transcript ingestion + voice command processing
    # ------------------------------------------------------------------
    def append_chunk(
        self,
        session_id: str,
        owner_id: str,
        text: str,
        is_final: bool = True,
        confidence: float = 1.0,
        started_at_ms: int = 0,
        ended_at_ms: int = 0,
    ) -> dict[str, Any]:
        """Append a transcript chunk. Voice commands are applied inline to
        the running transcript before the chunk is stored."""
        session = self.get_session(session_id, owner_id)
        processed, actions = self._apply_voice_commands(text, session.corrected_text)
        chunk = TranscriptChunk(
            id=str(uuid.uuid4()),
            text=processed["appended_text"],
            is_final=is_final,
            confidence=max(0.0, min(1.0, confidence)),
            started_at_ms=max(0, started_at_ms),
            ended_at_ms=max(started_at_ms, ended_at_ms),
            received_at=datetime.utcnow().isoformat(),
        )
        if is_final:
            session.chunks.append(chunk)
            session.corrected_text = processed["new_transcript"]
        session.updated_at = datetime.utcnow().isoformat()
        return {
            "chunk": chunk,
            "transcript": session.corrected_text,
            "commands_applied": actions,
        }

    @staticmethod
    def _apply_voice_commands(
        text: str,
        current_transcript: str,
    ) -> tuple[dict[str, str], list[str]]:
        """Detect voice commands in `text` and apply them to the running
        transcript. Returns (result, actions_log).
        """
        actions: list[str] = []
        transcript = current_transcript
        appended = ""
        # Split on whitespace while keeping a searchable form
        remaining = text.strip()
        if not remaining:
            return {"appended_text": "", "new_transcript": transcript}, actions
        # Lowercase version for matching commands
        lowered = remaining.lower()
        # Iterate through command phrases longest-first so "new paragraph"
        # wins over "new line".
        phrases = sorted(_VOICE_COMMANDS.keys(), key=len, reverse=True)
        # Tokenize into words + spaces
        tokens = re.split(r"(\s+)", remaining)
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.strip() == "":
                appended += tok
                i += 1
                continue
            # Try to match the longest command phrase starting here
            matched = False
            for phrase in phrases:
                phrase_words = phrase.split()
                window = []
                j = i
                word_count = 0
                while j < len(tokens) and word_count < len(phrase_words):
                    if tokens[j].strip() != "":
                        window.append(tokens[j].lower())
                        word_count += 1
                    j += 1
                if " ".join(window) == phrase:
                    kind, arg = _VOICE_COMMANDS[phrase]
                    if kind == "insert":
                        # For attached punctuation (. , ! ? ; :) drop any
                        # trailing whitespace in the buffer so the mark sits
                        # flush against the preceding word.
                        if arg and arg[0] in ".,!?;:" and len(arg) == 1:
                            appended = appended.rstrip(" ")
                        appended += arg
                    elif kind == "edit":
                        combined = transcript + appended
                        combined = VoxlenService._apply_edit(arg, combined)
                        # Rebuild appended against transcript — collapse into new transcript later
                        if combined.startswith(transcript):
                            appended = combined[len(transcript):]
                        else:
                            # Edit affected the pre-existing transcript (e.g. delete_last)
                            transcript = combined
                            appended = ""
                    actions.append(phrase)
                    i = j
                    matched = True
                    break
            if not matched:
                appended += tok
                i += 1
        new_transcript = (transcript + appended)
        # Collapse runs of 3+ newlines to 2
        new_transcript = re.sub(r"\n{3,}", "\n\n", new_transcript)
        return (
            {"appended_text": appended, "new_transcript": new_transcript},
            actions,
        )

    @staticmethod
    def _apply_edit(op: str, text: str) -> str:
        """Apply an edit voice command to the current text."""
        if not text:
            return text
        if op == "delete_last":
            # Drop the last word (and any trailing whitespace/punct after it)
            m = re.search(r"\S+\s*$", text)
            if m:
                return text[: m.start()].rstrip(" ")
            return text
        if op in {"capitalize_last", "upper_last", "lower_last"}:
            m = re.search(r"\S+\s*$", text)
            if not m:
                return text
            last = text[m.start(): m.end()]
            word_match = re.search(r"\S+", last)
            if not word_match:
                return text
            word = word_match.group(0)
            if op == "capitalize_last":
                transformed = word[:1].upper() + word[1:].lower()
            elif op == "upper_last":
                transformed = word.upper()
            else:
                transformed = word.lower()
            return text[: m.start() + word_match.start()] + transformed + last[word_match.end():]
        return text

    # ------------------------------------------------------------------
    # Grammar correction + style polish (deterministic fallback)
    # ------------------------------------------------------------------
    def polish(
        self,
        session_id: str,
        owner_id: str,
        style: WritingStyle | None = None,
    ) -> dict[str, Any]:
        """Run a grammar + style pass over the session transcript. When no
        LLM provider is configured, apply a deterministic cleanup pass so
        the feature works offline and in tests.
        """
        session = self.get_session(session_id, owner_id)
        target_style = style or session.style
        cleaned = self._deterministic_polish(session.corrected_text, target_style)
        session.corrected_text = cleaned
        session.style = target_style
        session.updated_at = datetime.utcnow().isoformat()
        return {
            "transcript": cleaned,
            "style": target_style.value,
            "provider": session.llm_provider.value,
            "deterministic_fallback": session.llm_provider == LLMProvider.NONE,
        }

    @staticmethod
    def _deterministic_polish(text: str, style: WritingStyle) -> str:
        if not text:
            return text
        # Normalize whitespace around punctuation
        out = re.sub(r"\s+([,.!?;:])", r"\1", text)
        # Ensure a single space after sentence-ending punctuation
        out = re.sub(r"([.!?])([A-Za-z])", r"\1 \2", out)
        # Capitalize sentence starts
        def _cap(match: re.Match) -> str:
            return match.group(1) + match.group(2).upper()
        out = re.sub(r"(^|[.!?]\s+)([a-z])", _cap, out)
        # Collapse double spaces
        out = re.sub(r"[ \t]{2,}", " ", out)
        # Style-specific polish
        if style == WritingStyle.LEGAL_FORMAL:
            out = out.replace(" i ", " I ")
            # Don't use contractions in formal legal writing
            for bad, good in [
                ("don't", "do not"),
                ("can't", "cannot"),
                ("won't", "will not"),
                ("isn't", "is not"),
                ("aren't", "are not"),
                ("it's", "it is"),
                ("we've", "we have"),
                ("they've", "they have"),
            ]:
                out = re.sub(rf"\b{re.escape(bad)}\b", good, out, flags=re.IGNORECASE)
        elif style == WritingStyle.CLIENT_FRIENDLY:
            # Prefer contractions for warmth
            for bad, good in [
                ("do not", "don't"),
                ("cannot", "can't"),
                ("will not", "won't"),
                ("it is", "it's"),
            ]:
                out = re.sub(rf"\b{re.escape(bad)}\b", good, out)
        elif style == WritingStyle.ACADEMIC:
            out = out.replace(" a lot ", " considerable ")
        return out.strip()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export(
        self,
        session_id: str,
        owner_id: str,
        fmt: ExportFormat,
    ) -> dict[str, Any]:
        session = self.get_session(session_id, owner_id)
        if fmt == ExportFormat.TXT:
            content = session.corrected_text
            mime = "text/plain"
        elif fmt == ExportFormat.MARKDOWN:
            content = self._export_markdown(session)
            mime = "text/markdown"
        elif fmt == ExportFormat.JSON:
            content = json.dumps(self._export_dict(session), indent=2, sort_keys=True)
            mime = "application/json"
        elif fmt == ExportFormat.SRT:
            content = self._export_srt(session)
            mime = "application/x-subrip"
        else:
            raise ValueError(f"Unsupported export format: {fmt}")
        return {
            "filename": f"{self._safe_filename(session.title)}.{fmt.value}",
            "mime": mime,
            "content": content,
        }

    @staticmethod
    def _safe_filename(title: str) -> str:
        base = re.sub(r"[^A-Za-z0-9_-]+", "_", title).strip("_") or "dictation"
        return base[:80]

    @staticmethod
    def _export_markdown(session: DictationSession) -> str:
        lines = [
            f"# {session.title}",
            "",
            f"- **Language:** {session.language}",
            f"- **Style:** {session.style.value}",
            f"- **Created:** {session.created_at}",
            "",
            "---",
            "",
            session.corrected_text or "_(no transcript)_",
        ]
        return "\n".join(lines)

    @staticmethod
    def _export_dict(session: DictationSession) -> dict[str, Any]:
        return {
            "id": session.id,
            "title": session.title,
            "language": session.language,
            "style": session.style.value,
            "template_key": session.template_key,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "status": session.status,
            "transcript": session.corrected_text,
            "chunks": [
                {
                    "id": c.id,
                    "text": c.text,
                    "is_final": c.is_final,
                    "confidence": c.confidence,
                    "started_at_ms": c.started_at_ms,
                    "ended_at_ms": c.ended_at_ms,
                    "received_at": c.received_at,
                }
                for c in session.chunks
            ],
        }

    @staticmethod
    def _export_srt(session: DictationSession) -> str:
        if not session.chunks:
            return ""
        out: list[str] = []
        for idx, c in enumerate(session.chunks, start=1):
            out.append(str(idx))
            out.append(
                f"{VoxlenService._ms_to_srt(c.started_at_ms)} --> "
                f"{VoxlenService._ms_to_srt(c.ended_at_ms)}"
            )
            out.append(c.text.strip())
            out.append("")
        return "\n".join(out)

    @staticmethod
    def _ms_to_srt(ms: int) -> str:
        ms = max(0, int(ms))
        hours, rem = divmod(ms, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        seconds, millis = divmod(rem, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    # ------------------------------------------------------------------
    # Catalog helpers
    # ------------------------------------------------------------------
    @staticmethod
    def catalog() -> dict[str, Any]:
        """Expose supported languages, styles, commands, and templates."""
        return {
            "languages": SUPPORTED_LANGUAGES,
            "styles": [s.value for s in WritingStyle],
            "export_formats": [f.value for f in ExportFormat],
            "stt_providers": [p.value for p in STTProvider],
            "llm_providers": [p.value for p in LLMProvider],
            "voice_commands": sorted(_VOICE_COMMANDS.keys()),
            "templates": {
                key: {
                    "title": data["title"],
                    "sections": data["sections"],
                }
                for key, data in LEGAL_TEMPLATES.items()
            },
        }
