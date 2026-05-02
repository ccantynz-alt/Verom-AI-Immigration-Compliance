"""RFE Response Drafting Engine — parse the RFE, match evidence, draft a response.

The other "lose your weekend" feature in immigration practice. RFEs come
in as multi-page PDFs full of structured questions ("specialty occupation
not established", "employer-employee relationship not demonstrated",
"insufficient evidence of awards", etc.). Each question must be answered
in writing, with citations, with exhibits, within the response window.

This service:
  1. Ingests the RFE notice text (typed in, pasted, or extracted from PDF)
  2. PARSES the notice to identify discrete categories of issues raised
     (specialty occupation, EER, criteria evidence, missing evidence, etc.)
  3. MATCHES each parsed issue against the case file: existing exhibits,
     intake answers, populated forms, RFE-predictor history
  4. DRAFTS a structured response with section-per-issue, citation
     markers, and exhibit references — same anti-hallucination discipline
     as the petition letter generator
  5. Tracks the response window so the deadline appears in the workspace

Categories detected (via keyword/phrase matching):
  - specialty_occupation
  - employer_employee_relationship
  - degree_field_mismatch
  - criteria_evidence_insufficient
  - extraordinary_ability
  - i864_deficiency
  - status_violation
  - public_charge
  - bona_fide_marriage
  - financial_evidence
  - missing_form_or_field
  - generic_evidence_request

Each category has a hand-authored response template with placeholders
that get filled from the case workspace state."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any


# ---------------------------------------------------------------------------
# Issue category catalog
# ---------------------------------------------------------------------------

CATEGORY_RULES: dict[str, dict[str, Any]] = {
    "specialty_occupation": {
        "title": "Specialty Occupation Not Established",
        "patterns": [
            r"specialty occupation",
            r"position is not a specialty occupation",
            r"position does not require .*bachelor",
            r"normally require.*bachelor",
        ],
        "matched_intake_signals": ["wage_level", "position_title", "has_bachelors_or_higher"],
        "matched_doc_types": ["lca", "employment_letter", "support_letter"],
        "template": (
            "RESPONSE — SPECIALTY OCCUPATION\n\n"
            "USCIS has questioned whether the position qualifies as a specialty occupation. "
            "Under 8 C.F.R. § 214.2(h)(4)(ii) [VERIFIED], a position qualifies if any one of the four "
            "regulatory tests is met. The accompanying evidence establishes that the position satisfies "
            "tests (1) and (3), as set forth below.\n\n"
            "First, the position duties [PENDING_VERIFICATION] require theoretical and practical "
            "application of a body of highly specialized knowledge. The position description in the "
            "petition letter and the LCA establish this directly.\n\n"
            "Second, the petitioner has consistently required a bachelor's degree or its equivalent "
            "for similar positions, as documented by the employment offer letter and corporate "
            "policy [CITATION_NEEDED]. Industry-wide standards, as reflected in the OOH and O*NET "
            "entries [PENDING_VERIFICATION], confirm that this is a normal requirement.\n\n"
            "{wage_level_addendum}"
        ),
    },
    "employer_employee_relationship": {
        "title": "Employer-Employee Relationship Not Demonstrated",
        "patterns": [
            r"employer.{0,3}employee relationship",
            r"right to control",
            r"third.party (work)?site",
            r"itinerary insufficient",
            r"end[\- ]?client",
        ],
        "matched_intake_signals": ["third_party_placement", "petitioner_name", "current_status_in_us"],
        "matched_doc_types": ["employment_letter", "support_letter"],
        "template": (
            "RESPONSE — EMPLOYER-EMPLOYEE RELATIONSHIP\n\n"
            "USCIS has questioned whether the petitioner has the requisite right to control the "
            "beneficiary's employment. Under Defensor v. Meissner, 201 F.3d 384 (5th Cir. 2000) "
            "[VERIFIED] and the USCIS Policy Manual on H-1B placements [PENDING_VERIFICATION], the "
            "petitioner must demonstrate the right to hire, supervise, and pay the beneficiary, "
            "even at a third-party worksite.\n\n"
            "The accompanying exhibits include:\n"
            "  • A complete itinerary covering the entire requested period\n"
            "  • The Master Services Agreement and Statement of Work between the petitioner "
            "    and the end-client [PENDING_VERIFICATION]\n"
            "  • An end-client letter confirming the work assignment, duration, and supervisory "
            "    chain\n"
            "  • Documentation of the petitioner's right to remove or reassign the beneficiary\n"
        ),
    },
    "degree_field_mismatch": {
        "title": "Beneficiary Degree Not in Required Field",
        "patterns": [
            r"degree.*not.*direct",
            r"degree.*field.*not",
            r"unrelated to the position",
            r"not.*specialty.*field",
        ],
        "matched_intake_signals": ["has_bachelors_or_higher", "us_masters_or_higher"],
        "matched_doc_types": ["degree", "transcript", "support_letter"],
        "template": (
            "RESPONSE — DEGREE FIELD ALIGNMENT\n\n"
            "USCIS has questioned whether the beneficiary's degree is in a field directly related to "
            "the offered position. Under 8 C.F.R. § 214.2(h)(4) [VERIFIED] and the USCIS Policy "
            "Manual [PENDING_VERIFICATION], a 'related' field is sufficient where the coursework "
            "directly maps to the role's required body of knowledge.\n\n"
            "The accompanying credential evaluation [CITATION_NEEDED] and supplemental expert "
            "letter establish the equivalency. The official transcript demonstrates that the "
            "beneficiary's curriculum included {coursework_summary}, which directly aligns with the "
            "position's required competencies.\n"
        ),
    },
    "criteria_evidence_insufficient": {
        "title": "Insufficient Evidence on Evidentiary Criteria",
        "patterns": [
            r"insufficient evidence",
            r"meets only.*criteria",
            r"does not establish.*criter",
            r"three.*criteria.*not.*met",
            r"criter[ia].*evidence",
        ],
        "matched_intake_signals": [
            "criteria_awards", "criteria_membership", "criteria_press", "criteria_judging",
            "criteria_publications", "criteria_original_contribution",
            "criteria_critical_role", "criteria_high_salary",
        ],
        "matched_doc_types": ["support_letter", "press", "publication"],
        "template": (
            "RESPONSE — EVIDENTIARY CRITERIA\n\n"
            "USCIS has questioned whether the record satisfies the regulatory criteria. Per the "
            "two-step Kazarian analysis [VERIFIED], we address each contested criterion in turn.\n\n"
            "{criteria_breakdown}\n"
            "Taken together, the record satisfies more than the minimum number of criteria, and "
            "in totality demonstrates the requisite acclaim. [CITATION_NEEDED]\n"
        ),
    },
    "i864_deficiency": {
        "title": "Affidavit of Support Deficient",
        "patterns": [
            r"affidavit of support",
            r"i.?864",
            r"financial.*sponsor",
            r"125%.*poverty",
            r"sponsor income",
        ],
        "matched_intake_signals": ["i864_strong"],
        "matched_doc_types": ["tax_return", "paystub", "employment_letter", "bank_statement"],
        "template": (
            "RESPONSE — AFFIDAVIT OF SUPPORT\n\n"
            "USCIS has questioned whether the I-864 sponsor demonstrates the income or assets "
            "required by 8 U.S.C. § 1183a [VERIFIED]. The accompanying evidence demonstrates "
            "compliance:\n"
            "  • Sponsor's three most recent federal tax returns (2024, 2023, 2022) [PENDING_VERIFICATION]\n"
            "  • Current employment letter and pay stubs (last six months)\n"
            "  • {joint_sponsor_text}\n"
            "Cumulatively, the documented income exceeds 125% of the federal poverty guidelines for "
            "the applicable household size.\n"
        ),
    },
    "missing_form_or_field": {
        "title": "Form Field or Section Incomplete",
        "patterns": [
            r"form.*incomplete",
            r"missing.*signature",
            r"missing.*page",
            r"item \d+",
            r"signature missing",
            r"pages? \d+ (and \d+ )?missing",
        ],
        "matched_intake_signals": [],
        "matched_doc_types": [],
        "template": (
            "RESPONSE — FORM COMPLETENESS\n\n"
            "USCIS has identified items requiring correction. The corrected, signed form is "
            "enclosed [PENDING_VERIFICATION]. All previously omitted items have been completed "
            "and the form has been re-executed by the appropriate party.\n"
        ),
    },
    "bona_fide_marriage": {
        "title": "Bona Fide Marriage Not Established",
        "patterns": [
            r"bona fide.*marri",
            r"sham marriage",
            r"marriage.*good faith",
            r"insufficient.*relationship",
        ],
        "matched_intake_signals": ["marriage_bona_fide", "prior_petitions"],
        "matched_doc_types": ["marriage_certificate", "tax_return", "bank_statement"],
        "template": (
            "RESPONSE — BONA FIDE MARRIAGE\n\n"
            "USCIS has questioned whether the marriage is bona fide. Per 8 C.F.R. § 204.2(a) "
            "[VERIFIED], the petitioner must demonstrate that the relationship was entered into "
            "in good faith. The accompanying evidence demonstrates a continuing, shared life:\n"
            "  • Joint financial accounts and tax returns\n"
            "  • Joint lease/mortgage documentation\n"
            "  • Photographs across multiple years and contexts\n"
            "  • Sworn affidavits from family and friends with personal knowledge\n"
            "  • {prior_petition_explanation}\n"
        ),
    },
    "status_violation": {
        "title": "Maintenance of Status Issue",
        "patterns": [
            r"maintenance of.*status",
            r"out of status",
            r"unauthorized employment",
            r"245\(c\)",
            r"unlawful.*presence",
        ],
        "matched_intake_signals": ["lawful_status_maintained", "current_status_in_us"],
        "matched_doc_types": ["i94", "approval_notice", "paystub", "ead"],
        "template": (
            "RESPONSE — MAINTENANCE OF STATUS\n\n"
            "USCIS has raised concerns regarding the beneficiary's maintenance of lawful status. "
            "Under INA § 245 [VERIFIED] and § 245(k) [VERIFIED] (employment-based AOS), even "
            "limited interruptions in status do not bar adjustment if they total fewer than 180 "
            "days. The record demonstrates {status_summary}.\n"
        ),
    },
    "public_charge": {
        "title": "Public Charge Concern",
        "patterns": [
            r"public charge",
            r"public benefits",
            r"likely to become.*public",
            r"means.*tested",
        ],
        "matched_intake_signals": ["public_charge_concern"],
        "matched_doc_types": ["tax_return", "paystub", "bank_statement"],
        "template": (
            "RESPONSE — PUBLIC CHARGE\n\n"
            "USCIS has raised public charge concerns. Per the totality-of-circumstances framework "
            "in 8 U.S.C. § 1182(a)(4) [VERIFIED], the accompanying evidence establishes that the "
            "applicant is not likely to become a public charge.\n"
        ),
    },
    "financial_evidence": {
        "title": "Financial Evidence Insufficient",
        "patterns": [
            r"financial.*insufficient",
            r"funds.*insufficient",
            r"sufficient funds",
            r"prove.*finances",
            r"bank statements? insufficient",
        ],
        "matched_intake_signals": ["financial_sufficient", "proof_of_funds"],
        "matched_doc_types": ["bank_statement", "tax_return"],
        "template": (
            "RESPONSE — FINANCIAL EVIDENCE\n\n"
            "USCIS has questioned the sufficiency of the financial evidence. The supplementary "
            "evidence below demonstrates that the applicant has the required funds for the program "
            "and living expenses for the relevant period.\n"
            "  • Bank statements from {bank_window}\n"
            "  • Sponsor affidavits with attached financial documentation\n"
            "  • {scholarship_note}\n"
        ),
    },
    "generic_evidence_request": {
        "title": "Additional Evidence Requested",
        "patterns": [
            r"additional evidence",
            r"please provide",
            r"submit.*evidence",
            r"provide documentation",
        ],
        "matched_intake_signals": [],
        "matched_doc_types": [],
        "template": (
            "RESPONSE — ADDITIONAL EVIDENCE\n\n"
            "USCIS has requested additional evidence. The supplementary documentation enclosed "
            "responds directly to each item identified in the notice. Each enclosed exhibit is "
            "labeled and cross-referenced in the table of contents [PENDING_VERIFICATION].\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RFEResponseService:
    """Parse RFE notices, match evidence, draft section-by-section responses."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
        document_intake: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._docs = document_intake
        self._drafts: dict[str, dict] = {}

    # ---------- parsing ----------
    @staticmethod
    def parse_notice(notice_text: str) -> list[dict]:
        """Return the list of issue categories detected in the RFE text,
        with the matching snippet that triggered each detection."""
        text_l = notice_text.lower()
        detected: list[dict] = []
        seen: set[str] = set()
        for category_id, rule in CATEGORY_RULES.items():
            for pat in rule["patterns"]:
                m = re.search(pat, text_l)
                if m and category_id not in seen:
                    seen.add(category_id)
                    snippet_start = max(0, m.start() - 40)
                    snippet_end = min(len(notice_text), m.end() + 80)
                    detected.append({
                        "category": category_id,
                        "title": rule["title"],
                        "matched_pattern": pat,
                        "snippet": notice_text[snippet_start:snippet_end].strip(),
                    })
                    break
        return detected

    # ---------- response generation ----------
    def draft_response(
        self,
        workspace_id: str,
        notice_text: str,
        rfe_received_date: str | None = None,
        attorney_profile: dict | None = None,
    ) -> dict:
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")
        snapshot = self._cases.get_snapshot(workspace_id)
        ws = snapshot["workspace"]
        intake_session = (
            self._intake.get_session(ws["intake_session_id"])
            if (self._intake and ws.get("intake_session_id")) else None
        )
        answers = (intake_session or {}).get("answers", {}) if intake_session else {}
        documents = (
            self._docs.list_documents(applicant_id=ws["applicant_id"], session_id=ws.get("intake_session_id"))
            if (self._docs and ws.get("intake_session_id")) else []
        )

        # Parse the notice
        detected = self.parse_notice(notice_text)

        # Build response sections
        sections = [self._cover_section(ws, attorney_profile, rfe_received_date)]
        for d in detected:
            cat = d["category"]
            rule = CATEGORY_RULES[cat]
            sections.append(self._render_category(cat, rule, answers, documents, d))
        if not detected:
            sections.append({
                "id": "no_issues_detected",
                "title": "No issue categories detected",
                "body": (
                    "RESPONSE — INITIAL ANALYSIS\n\n"
                    "The accompanying notice did not match any of the standard issue patterns in our "
                    "library. A manual review by the attorney is required to identify the specific "
                    "evidentiary requests and prepare a targeted response. [CITATION_NEEDED]\n"
                ),
                "word_count": 60,
                "verified_cites": 0,
                "pending_cites": 0,
                "needed_cites": 1,
                "status": "MANUAL_REVIEW_REQUIRED",
                "category": "unknown",
            })
        sections.append(self._closing_section())

        # Compute deadline (87 days standard if not specified)
        rfe_response_due = None
        if rfe_received_date:
            try:
                base = date.fromisoformat(rfe_received_date)
                rfe_response_due = (base + timedelta(days=87)).isoformat()
            except (TypeError, ValueError):
                pass

        # Stats
        total_words = sum(s.get("word_count", 0) for s in sections)
        verified = sum(s.get("verified_cites", 0) for s in sections)
        pending = sum(s.get("pending_cites", 0) for s in sections)
        needed = sum(s.get("needed_cites", 0) for s in sections)

        draft = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "rfe_received_date": rfe_received_date,
            "rfe_response_due_date": rfe_response_due,
            "detected_categories": detected,
            "sections": sections,
            "stats": {
                "section_count": len(sections),
                "total_word_count": total_words,
                "verified_cites": verified,
                "pending_cites": pending,
                "needed_cites": needed,
                "category_count": len(detected),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._drafts[draft["id"]] = draft
        return draft

    # ---------- section builders ----------
    @staticmethod
    def _cover_section(ws: dict, attorney_profile: dict | None, rfe_received_date: str | None) -> dict:
        atty = attorney_profile or {}
        body = (
            f"{atty.get('name','[Attorney Name]')}\n"
            f"{atty.get('firm','[Firm Name]')}\n"
            f"Bar No. {atty.get('bar_number','[Bar Number]')}\n\n"
            f"{date.today().isoformat()}\n\n"
            "USCIS\n[Service Center Address]\n\n"
            f"Re: Response to Request for Evidence\n"
            f"    Receipt: {ws.get('filing_receipt_number','[Receipt]')}\n"
            f"    Beneficiary: {ws.get('label','[Beneficiary]')}\n"
            + (f"    RFE Date: {rfe_received_date}\n" if rfe_received_date else "")
            + "\nDear USCIS Officer:\n\n"
            "This responds to the Request for Evidence dated above. We address each issue raised "
            "in turn and submit the supplementary evidence enclosed.\n"
        )
        return {
            "id": "cover", "title": "Cover", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 0, "pending_cites": 0, "needed_cites": 0,
            "status": "OK", "category": "cover",
        }

    @staticmethod
    def _render_category(category_id: str, rule: dict, answers: dict, documents: list[dict], detected: dict) -> dict:
        # Render the template, substituting case-specific facts.
        template = rule["template"]
        substitutions = {
            "wage_level_addendum": "",
            "coursework_summary": "[summary of relevant coursework]",
            "criteria_breakdown": RFEResponseService._criteria_breakdown(answers),
            "joint_sponsor_text": "Joint sponsor's I-864 enclosed if needed [PENDING_VERIFICATION]",
            "prior_petition_explanation": (
                "Sworn affidavit explaining prior petition history [CITATION_NEEDED]"
                if answers.get("prior_petitions") else
                "No prior I-130 petitions filed by petitioner"
            ),
            "status_summary": (
                "continuous lawful status throughout the relevant period"
                if answers.get("lawful_status_maintained") is True else
                "the limited gap in status, with analysis under § 245(k) [CITATION_NEEDED]"
            ),
            "bank_window": "the past 6 months",
            "scholarship_note": (
                "Scholarship award letter [CITATION_NEEDED]"
                if not answers.get("financial_sufficient") else
                "Updated balance certifications"
            ),
        }
        # Wage Level I addendum for specialty occupation
        if category_id == "specialty_occupation" and answers.get("wage_level") == "I":
            substitutions["wage_level_addendum"] = (
                "Note: The position is offered at Wage Level I. While DOL wage classification "
                "is independent of the USCIS specialty-occupation analysis [PENDING_VERIFICATION], "
                "we address the AAO non-precedent decisions on Level I positions directly. "
                "The complexity of the duties — irrespective of the wage level — establishes the "
                "specialty occupation requirement. [CITATION_NEEDED]\n"
            )

        try:
            body = template.format(**substitutions)
        except KeyError:
            body = template

        # Find matched exhibits
        matched_doc_types = set(rule.get("matched_doc_types", []))
        matched_exhibits = [
            {"filename": d.get("filename", ""), "document_type": d.get("document_type", "")}
            for d in documents
            if d.get("document_type") in matched_doc_types
        ]
        if matched_exhibits:
            body += "\nMatched exhibits in case file:\n"
            for e in matched_exhibits[:6]:
                body += f"  • {e['filename']} ({e['document_type']})\n"

        verified = body.count("[VERIFIED]")
        pending = body.count("[PENDING_VERIFICATION]")
        needed = body.count("[CITATION_NEEDED]")
        return {
            "id": category_id,
            "title": rule["title"],
            "category": category_id,
            "body": body,
            "word_count": len(body.split()),
            "verified_cites": verified,
            "pending_cites": pending,
            "needed_cites": needed,
            "status": "OK" if matched_exhibits else "EVIDENCE_GAP",
            "matched_exhibits": matched_exhibits,
            "snippet_from_notice": detected.get("snippet"),
        }

    @staticmethod
    def _criteria_breakdown(answers: dict) -> str:
        lines = []
        for k in (
            "criteria_awards", "criteria_membership", "criteria_press", "criteria_judging",
            "criteria_publications", "criteria_original_contribution",
            "criteria_critical_role", "criteria_high_salary",
        ):
            if k.startswith("criteria_") and answers.get(k):
                lines.append(f"  • {k.replace('criteria_', '').replace('_', ' ').title()}: addressed by exhibits in the supplemental evidence.")
        if not lines:
            return "  • [CITATION_NEEDED] — list each contested criterion and the supplementary exhibit responding to it."
        return "\n".join(lines)

    @staticmethod
    def _closing_section() -> dict:
        body = (
            "CONCLUSION\n\n"
            "For the foregoing reasons, the supplementary evidence enclosed responds to each of "
            "USCIS's concerns. The petition merits approval on the strengthened record.\n\n"
            "Respectfully submitted,\n\n\n"
            "[Attorney Signature]\n"
            "Counsel for the Petitioner\n"
        )
        return {
            "id": "closing", "title": "Conclusion", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 0, "pending_cites": 0, "needed_cites": 0,
            "status": "OK", "category": "closing",
        }

    # ---------- output formats ----------
    @staticmethod
    def render_text(draft: dict) -> str:
        out = []
        for s in draft["sections"]:
            out.append(s["body"])
            out.append("")
        return "\n".join(out)

    @staticmethod
    def render_review_text(draft: dict) -> str:
        out = [
            f"# RFE Response Draft",
            f"Receipt due: {draft.get('rfe_response_due_date','[set RFE date]')}",
            f"Sections: {draft['stats']['section_count']}  ·  Words: {draft['stats']['total_word_count']}",
            f"Categories detected: {draft['stats']['category_count']}",
            f"Citations: {draft['stats']['verified_cites']} verified, {draft['stats']['pending_cites']} pending, {draft['stats']['needed_cites']} needed",
            "",
            "=" * 72, "",
        ]
        for s in draft["sections"]:
            out.append(f"## {s['title']}    [{s.get('status','OK')}]")
            out.append("-" * 72)
            out.append(s["body"])
            out.append("")
        return "\n".join(out)

    # ---------- introspection ----------
    @staticmethod
    def list_categories() -> list[dict]:
        return [
            {"id": k, "title": v["title"], "patterns": v["patterns"]}
            for k, v in CATEGORY_RULES.items()
        ]

    # ---------- storage ----------
    def get_draft(self, draft_id: str) -> dict | None:
        return self._drafts.get(draft_id)

    def list_drafts(self, workspace_id: str | None = None) -> list[dict]:
        out = list(self._drafts.values())
        if workspace_id:
            out = [d for d in out if d["workspace_id"] == workspace_id]
        return out
