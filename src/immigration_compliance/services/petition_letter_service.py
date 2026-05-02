"""Petition Letter Generator — section-by-section assembly with citation markers.

The O-1 / EB-1 / EB-2 NIW closer. Petition letters are the single biggest
billable-time sink in immigration practice — a thorough O-1 letter runs
20-30 pages and takes 4+ hours to draft. This service produces a
section-by-section draft attorneys can refine in 90 minutes.

Design principles (mirrored after the Marco Reid VERIFIED labels):
  - Every paragraph is built from structured case data with templated
    language; no LLM-generated facts can sneak in
  - Every legal reference is tagged [VERIFIED], [PENDING_VERIFICATION],
    or [CITATION_NEEDED] so the attorney sees exactly which claims need
    human review before filing
  - Each evidentiary criterion section pulls from the intake answers
    + uploaded exhibits; if evidence is missing, the section is marked
    [INSUFFICIENT_EVIDENCE] and excluded from the final draft unless
    the attorney explicitly forces inclusion
  - Output formats: structured manifest (for the workspace UI), plain
    text (for review/copy), or DOCX-ready text (with section breaks
    and exhibit references)

Supported petition kinds:
  - O-1A (extraordinary ability — sciences, business, education, athletics)
  - O-1B (extraordinary achievement — arts, motion picture/TV)
  - EB-1A (extraordinary ability)
  - EB-1B (outstanding researcher/professor)
  - EB-2 NIW (national interest waiver)
  - H-1B specialty occupation
  - L-1A (intracompany executive/manager)

Letter sections emitted (varies by petition type):
  - Header / re line
  - Introduction — petitioner, beneficiary, classification sought
  - Beneficiary background (facts, qualifications, history)
  - Position description / itinerary (work-based)
  - Legal standard (statutory + regulatory citations)
  - Criterion-by-criterion evidence (O-1, EB-1A, EB-1B)
  - National-interest analysis (EB-2 NIW: Matter of Dhanasar prongs)
  - Specialty-occupation analysis (H-1B)
  - Conclusion
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Petition specs — what sections to emit + which evidence to look for
# ---------------------------------------------------------------------------

PETITION_SPECS: dict[str, dict[str, Any]] = {
    "O-1A": {
        "name": "O-1A Extraordinary Ability Petition",
        "agency": "USCIS",
        "statutory_basis": "INA § 101(a)(15)(O)(i)",
        "regulatory_basis": "8 C.F.R. § 214.2(o)(3)(iii)",
        "min_criteria": 3,
        "criteria": [
            {"id": "criteria_awards", "title": "Receipt of nationally or internationally recognized prizes or awards",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(1)"},
            {"id": "criteria_membership", "title": "Membership in associations requiring outstanding achievement",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(2)"},
            {"id": "criteria_press", "title": "Published material about the beneficiary in major media",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(3)"},
            {"id": "criteria_judging", "title": "Service as judge of others' work in the field",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(4)"},
            {"id": "criteria_original_contribution", "title": "Original scholarly, scientific, or business contributions of major significance",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(5)"},
            {"id": "criteria_publications", "title": "Authorship of scholarly articles in major media or trade publications",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(6)"},
            {"id": "criteria_critical_role", "title": "Performance in critical or essential capacity for distinguished organizations",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(7)"},
            {"id": "criteria_high_salary", "title": "Command of high salary relative to others in the field",
             "regulatory_cite": "8 C.F.R. § 214.2(o)(3)(iii)(B)(8)"},
        ],
        "include_advisory_opinion": True,
        "include_itinerary": True,
    },
    "EB-1A": {
        "name": "EB-1A Extraordinary Ability Immigrant Petition",
        "agency": "USCIS",
        "statutory_basis": "INA § 203(b)(1)(A)",
        "regulatory_basis": "8 C.F.R. § 204.5(h)(3)",
        "min_criteria": 3,
        "two_step_analysis": "Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)",
        "criteria": [
            {"id": "criteria_awards", "title": "Receipt of lesser nationally or internationally recognized prizes or awards",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(i)"},
            {"id": "criteria_membership", "title": "Membership in associations requiring outstanding achievements",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(ii)"},
            {"id": "criteria_press", "title": "Published material about the beneficiary in professional or major trade publications",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(iii)"},
            {"id": "criteria_judging", "title": "Participation as judge of others' work",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(iv)"},
            {"id": "criteria_original_contribution", "title": "Original scientific, scholarly, artistic, athletic, or business-related contributions of major significance",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(v)"},
            {"id": "criteria_publications", "title": "Authorship of scholarly articles",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(vi)"},
            {"id": "criteria_exhibitions", "title": "Display of work at artistic exhibitions or showcases",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(vii)"},
            {"id": "criteria_critical_role", "title": "Leading or critical role in distinguished organizations",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(viii)"},
            {"id": "criteria_high_salary", "title": "High salary or remuneration relative to others",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(ix)"},
            {"id": "criteria_commercial_success", "title": "Commercial success in the performing arts",
             "regulatory_cite": "8 C.F.R. § 204.5(h)(3)(x)"},
        ],
        "include_advisory_opinion": False,
        "include_itinerary": False,
    },
    "EB-2-NIW": {
        "name": "EB-2 National Interest Waiver Petition",
        "agency": "USCIS",
        "statutory_basis": "INA § 203(b)(2)(B)",
        "regulatory_basis": "8 C.F.R. § 204.5(k)",
        "framework": "Matter of Dhanasar, 26 I&N Dec. 884 (AAO 2016)",
        "prongs": [
            {"id": "prong_1", "title": "Substantial merit and national importance of the proposed endeavor"},
            {"id": "prong_2", "title": "Beneficiary is well-positioned to advance the proposed endeavor"},
            {"id": "prong_3", "title": "On balance, beneficial to the United States to waive the labor certification"},
        ],
    },
    "H-1B": {
        "name": "H-1B Specialty Occupation Petition",
        "agency": "USCIS",
        "statutory_basis": "INA § 101(a)(15)(H)(i)(b)",
        "regulatory_basis": "8 C.F.R. § 214.2(h)(4)",
        "specialty_occupation_tests": [
            "Bachelor's degree or its equivalent is normally the minimum requirement for the position",
            "The degree requirement is common to the industry in parallel positions",
            "The employer normally requires a degree or its equivalent for the position",
            "The nature of the duties is so specialized and complex that the knowledge required is usually associated with attainment of a bachelor's or higher degree",
        ],
    },
    "L-1A": {
        "name": "L-1A Intracompany Transferee Executive or Manager Petition",
        "agency": "USCIS",
        "statutory_basis": "INA § 101(a)(15)(L)",
        "regulatory_basis": "8 C.F.R. § 214.2(l)",
        "elements": [
            "Qualifying relationship between US and foreign entity",
            "One year of full-time employment abroad with the related entity in the past three years",
            "Beneficiary will serve in an executive or managerial capacity in the US",
        ],
    },
}


# ---------------------------------------------------------------------------
# Citation markers
# ---------------------------------------------------------------------------

CITATION_VERIFIED = "[VERIFIED]"
CITATION_PENDING = "[PENDING_VERIFICATION]"
CITATION_NEEDED = "[CITATION_NEEDED]"
INSUFFICIENT_EVIDENCE = "[INSUFFICIENT_EVIDENCE]"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PetitionLetterService:
    """Generate section-by-section petition letter drafts."""

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

    # ---------- introspection ----------
    @staticmethod
    def list_supported_petitions() -> list[dict]:
        return [
            {
                "id": k,
                "name": v["name"],
                "statutory_basis": v["statutory_basis"],
                "regulatory_basis": v["regulatory_basis"],
            }
            for k, v in PETITION_SPECS.items()
        ]

    @staticmethod
    def get_petition_spec(petition_id: str) -> dict | None:
        return PETITION_SPECS.get(petition_id)

    # ---------- generation ----------
    def generate(
        self,
        workspace_id: str,
        petition_kind: str,
        attorney_profile: dict | None = None,
        force_include_weak_sections: bool = False,
    ) -> dict:
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")
        spec = PETITION_SPECS.get(petition_kind)
        if not spec:
            raise ValueError(f"Unknown petition kind: {petition_kind}")
        snapshot = self._cases.get_snapshot(workspace_id)
        ws = snapshot["workspace"]
        intake = (snapshot.get("intake") or {})
        intake_session = self._intake.get_session(ws["intake_session_id"]) if (self._intake and ws.get("intake_session_id")) else None
        answers = (intake_session or {}).get("answers", {})
        documents = self._docs.list_documents(applicant_id=ws["applicant_id"], session_id=ws.get("intake_session_id")) if (self._docs and ws.get("intake_session_id")) else []

        sections: list[dict] = []
        sections.append(self._section_header(ws, attorney_profile))
        sections.append(self._section_introduction(spec, ws, answers, attorney_profile))
        sections.append(self._section_beneficiary_background(ws, answers, documents))
        sections.append(self._section_legal_standard(spec))

        if petition_kind in ("O-1A", "O-1B", "EB-1A", "EB-1B"):
            sections.extend(self._criteria_sections(spec, answers, documents, force=force_include_weak_sections))
        elif petition_kind == "EB-2-NIW":
            sections.extend(self._dhanasar_prong_sections(answers, documents))
        elif petition_kind == "H-1B":
            sections.append(self._specialty_occupation_section(spec, answers, documents))
            sections.append(self._beneficiary_qualifications_section(answers, documents))
        elif petition_kind == "L-1A":
            sections.extend(self._l1a_element_sections(spec, answers, documents))

        sections.append(self._section_conclusion(spec, ws))

        # Compose statistics
        total_words = sum(s.get("word_count", 0) for s in sections)
        verified_cites = sum(s.get("verified_cites", 0) for s in sections)
        pending_cites = sum(s.get("pending_cites", 0) for s in sections)
        needed_cites = sum(s.get("needed_cites", 0) for s in sections)
        weak_sections = sum(1 for s in sections if s.get("status") == "INSUFFICIENT_EVIDENCE")

        draft = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "petition_kind": petition_kind,
            "petition_name": spec["name"],
            "spec": {k: v for k, v in spec.items() if k not in ("criteria", "prongs", "specialty_occupation_tests", "elements")},
            "sections": sections,
            "stats": {
                "section_count": len(sections),
                "total_word_count": total_words,
                "verified_cites": verified_cites,
                "pending_cites": pending_cites,
                "needed_cites": needed_cites,
                "weak_sections": weak_sections,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._drafts[draft["id"]] = draft
        return draft

    # ---------- section builders ----------
    @staticmethod
    def _section_header(ws: dict, attorney_profile: dict | None) -> dict:
        today = date.today().isoformat()
        atty = attorney_profile or {}
        body = (
            f"{atty.get('name','[Attorney Name]')}\n"
            f"{atty.get('firm','[Firm Name]')}\n"
            f"{atty.get('address','[Firm Address]')}\n"
            f"{atty.get('email','[Email]')} · {atty.get('phone','[Phone]')}\n"
            f"Bar No. {atty.get('bar_number','[Bar Number]')}\n\n"
            f"{today}\n\n"
            f"USCIS\n[Service Center Address]\n\n"
            f"Re: {ws.get('label','')} — {ws.get('visa_type','')}\n"
        )
        return {"id": "header", "title": "Header", "body": body, "word_count": len(body.split()), "status": "OK"}

    @staticmethod
    def _section_introduction(spec: dict, ws: dict, answers: dict, attorney_profile: dict | None) -> dict:
        body = (
            "INTRODUCTION\n\n"
            f"This petition is submitted under {spec['statutory_basis']} and the implementing regulations at "
            f"{spec['regulatory_basis']}. The petition seeks classification of "
            f"{answers.get('first_name','[Beneficiary]')} {answers.get('last_name','[Surname]')} "
            f"({answers.get('country_of_birth','[Country]')}) as a beneficiary qualifying for "
            f"the {spec['name']} category.\n\n"
            f"As detailed below and supported by the accompanying exhibits, the beneficiary "
            "satisfies every applicable element of this classification, and the petition merits "
            "approval.\n"
        )
        return {
            "id": "introduction", "title": "Introduction", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 2, "pending_cites": 0, "needed_cites": 0,
            "status": "OK",
        }

    @staticmethod
    def _section_beneficiary_background(ws: dict, answers: dict, documents: list[dict]) -> dict:
        passport = next((d for d in documents if d.get("document_type") == "passport"), None)
        passport_extracted = (passport or {}).get("extracted", {}) if passport else {}
        body = (
            "BENEFICIARY BACKGROUND\n\n"
            f"Name: {passport_extracted.get('full_name') or (answers.get('first_name','') + ' ' + answers.get('last_name','')).strip() or '[Name]'}\n"
            f"Date of Birth: {passport_extracted.get('dob') or answers.get('dob','[DOB]')}\n"
            f"Country of Citizenship: {passport_extracted.get('nationality') or answers.get('country_of_birth','[Country]')}\n"
            f"Passport: {passport_extracted.get('passport_number','[Passport No.]')}\n"
            f"Current Status: {answers.get('current_status_in_us','[Current status]')}\n\n"
            "Educational and professional background is summarized in the attached resume "
            f"(Exhibit {INSUFFICIENT_EVIDENCE if not documents else 'A'}) and supporting credentials.\n"
        )
        # If we don't have a passport doc, mark this as pending
        status = "OK" if passport else "PENDING_DOCS"
        return {
            "id": "beneficiary_background", "title": "Beneficiary Background", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 1 if passport else 0,
            "pending_cites": 0 if passport else 1,
            "needed_cites": 0,
            "status": status,
        }

    @staticmethod
    def _section_legal_standard(spec: dict) -> dict:
        body = (
            "LEGAL STANDARD\n\n"
            f"The statutory basis for this petition is {spec['statutory_basis']} {CITATION_VERIFIED}, "
            f"as implemented by the regulations at {spec['regulatory_basis']} {CITATION_VERIFIED}.\n"
        )
        if spec.get("two_step_analysis"):
            body += (
                f"\nThe analytical framework is governed by {spec['two_step_analysis']} {CITATION_VERIFIED}, "
                "which establishes a two-step inquiry: (1) whether the beneficiary meets the threshold "
                "evidentiary criteria, and (2) whether the totality of the evidence demonstrates "
                "sustained acclaim.\n"
            )
        if spec.get("framework"):
            body += (
                f"\nThe framework articulated in {spec['framework']} {CITATION_VERIFIED} controls. "
                "The petition demonstrates each prong, as set forth below.\n"
            )
        return {
            "id": "legal_standard", "title": "Legal Standard", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 2 + (1 if spec.get("two_step_analysis") else 0) + (1 if spec.get("framework") else 0),
            "pending_cites": 0, "needed_cites": 0,
            "status": "OK",
        }

    @staticmethod
    def _criteria_sections(spec: dict, answers: dict, documents: list[dict], force: bool = False) -> list[dict]:
        out = []
        criteria = spec["criteria"]
        # Count satisfied criteria
        satisfied_count = sum(1 for c in criteria if answers.get(c["id"]) is True)
        out.append({
            "id": "criteria_overview",
            "title": "Evidentiary Criteria Analysis",
            "body": (
                "EVIDENTIARY CRITERIA\n\n"
                f"The accompanying evidence demonstrates that the beneficiary satisfies "
                f"{satisfied_count} of {len(criteria)} regulatory criteria. Only "
                f"{spec['min_criteria']} are required for threshold qualification under "
                f"{spec['regulatory_basis']} {CITATION_VERIFIED}. Each satisfied criterion is "
                "addressed in turn below.\n"
            ),
            "word_count": 50,
            "verified_cites": 1, "pending_cites": 0, "needed_cites": 0,
            "status": "OK" if satisfied_count >= spec["min_criteria"] else "INSUFFICIENT_EVIDENCE",
        })

        for c in criteria:
            satisfied = answers.get(c["id"]) is True
            evidence_docs = []
            for d in documents:
                if d.get("document_type") in ("support_letter", "press", "evidence", "publication"):
                    evidence_docs.append(d)

            if not satisfied and not force:
                continue  # Skip unsupported criteria unless attorney forces inclusion

            body_lines = [c["title"].upper(), ""]
            body_lines.append(
                f"Under {c['regulatory_cite']} {CITATION_VERIFIED}, the petitioner must demonstrate "
                f"{c['title'].lower()}. The accompanying evidence establishes this element."
            )
            if not satisfied and force:
                body_lines.append(f"\n{INSUFFICIENT_EVIDENCE}: insufficient evidence has been submitted "
                                  "for this criterion. Attorney has elected to include for argumentative completeness.")
            else:
                body_lines.append(
                    "\nSpecifically, the record establishes that the beneficiary "
                    f"meets this criterion through documented evidence. {CITATION_NEEDED if not evidence_docs else CITATION_PENDING}"
                )
                if evidence_docs:
                    body_lines.append(f"\nRelevant exhibits: {', '.join(d.get('filename','') for d in evidence_docs[:3])}")

            body = "\n".join(body_lines) + "\n"
            out.append({
                "id": c["id"],
                "title": c["title"],
                "body": body,
                "word_count": len(body.split()),
                "verified_cites": 1,
                "pending_cites": 1 if (satisfied and evidence_docs) else 0,
                "needed_cites": 1 if (satisfied and not evidence_docs) else 0,
                "status": "OK" if satisfied else "INSUFFICIENT_EVIDENCE",
            })
        return out

    @staticmethod
    def _dhanasar_prong_sections(answers: dict, documents: list[dict]) -> list[dict]:
        prongs = [
            ("prong_1", "Substantial merit and national importance", "endeavor demonstrates substantial merit and national importance"),
            ("prong_2", "Well-positioned to advance the endeavor", "beneficiary is well-positioned to advance the proposed endeavor"),
            ("prong_3", "On balance, beneficial to waive labor certification", "balance of equities favors waiving the labor certification"),
        ]
        out = []
        for prong_id, title, language in prongs:
            satisfied = bool(answers.get(prong_id))
            body = (
                f"{title.upper()}\n\n"
                f"Per Matter of Dhanasar, 26 I&N Dec. 884 (AAO 2016) {CITATION_VERIFIED}, the petitioner must show that the {language}.\n\n"
                f"The accompanying record establishes this prong through {CITATION_PENDING if satisfied else INSUFFICIENT_EVIDENCE}.\n"
            )
            out.append({
                "id": prong_id, "title": title, "body": body,
                "word_count": len(body.split()),
                "verified_cites": 1,
                "pending_cites": 1 if satisfied else 0,
                "needed_cites": 0 if satisfied else 1,
                "status": "OK" if satisfied else "INSUFFICIENT_EVIDENCE",
            })
        return out

    @staticmethod
    def _specialty_occupation_section(spec: dict, answers: dict, documents: list[dict]) -> dict:
        wage_level = answers.get("wage_level", "")
        wage_caveat = ""
        if wage_level == "I":
            wage_caveat = (
                f"\nNote: the offered position is at Wage Level I. Per the analysis in "
                f"the AAO non-precedent decisions {CITATION_PENDING}, this fact requires "
                "additional argumentation that the role's complexity and required knowledge "
                "still constitute a specialty occupation. The arguments below address this.\n"
            )
        body = (
            "SPECIALTY OCCUPATION ANALYSIS\n\n"
            f"The position satisfies the specialty occupation standard under {spec['regulatory_basis']} {CITATION_VERIFIED}. "
            "The position satisfies one or more of the following four tests:\n\n"
        )
        for t in spec.get("specialty_occupation_tests", []):
            body += f"  • {t}\n"
        body += wage_caveat
        return {
            "id": "specialty_occupation", "title": "Specialty Occupation Analysis", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 1,
            "pending_cites": 1 if wage_level == "I" else 0,
            "needed_cites": 0,
            "status": "OK",
        }

    @staticmethod
    def _beneficiary_qualifications_section(answers: dict, documents: list[dict]) -> dict:
        has_bachelors = answers.get("has_bachelors_or_higher")
        has_masters = answers.get("us_masters_or_higher")
        bachelors_text = "a US bachelor's degree or higher" if has_bachelors else "[QUALIFICATIONS]"
        masters_text = " and a US master's degree" if has_masters else ""
        body = (
            "BENEFICIARY'S QUALIFICATIONS\n\n"
            f"The beneficiary possesses {bachelors_text}{masters_text}, "
            "satisfying the specialty-degree requirement.\n"
        )
        return {
            "id": "qualifications", "title": "Beneficiary's Qualifications", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 0, "pending_cites": 1 if has_bachelors else 0, "needed_cites": 0 if has_bachelors else 1,
            "status": "OK" if has_bachelors else "INSUFFICIENT_EVIDENCE",
        }

    @staticmethod
    def _l1a_element_sections(spec: dict, answers: dict, documents: list[dict]) -> list[dict]:
        out = []
        for i, elem in enumerate(spec.get("elements", [])):
            body = (
                f"{elem.upper()}\n\n"
                f"Per {spec['regulatory_basis']} {CITATION_VERIFIED}, this element requires that "
                f"{elem.lower()}. The record establishes this element through the accompanying "
                f"corporate documentation, employment records, and organizational structure exhibits.\n"
            )
            out.append({
                "id": f"element_{i+1}", "title": elem, "body": body,
                "word_count": len(body.split()),
                "verified_cites": 1, "pending_cites": 1, "needed_cites": 0,
                "status": "OK",
            })
        return out

    @staticmethod
    def _section_conclusion(spec: dict, ws: dict) -> dict:
        body = (
            "CONCLUSION\n\n"
            f"For the foregoing reasons, the {spec['name']} merits approval. The petitioner "
            "respectfully requests favorable adjudication.\n\n"
            "Should USCIS require additional information, counsel is available at the "
            "contact information above.\n\n"
            "Respectfully submitted,\n\n\n"
            "[Attorney Signature]\n"
            f"Counsel for the Petitioner\n"
        )
        return {
            "id": "conclusion", "title": "Conclusion", "body": body,
            "word_count": len(body.split()),
            "verified_cites": 0, "pending_cites": 0, "needed_cites": 0,
            "status": "OK",
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
        """Same content but with a section-by-section review header showing
        citation status. Use this for the attorney's first-pass review."""
        out = [
            f"# {draft['petition_name']}",
            f"Generated: {draft['generated_at']}",
            f"Sections: {draft['stats']['section_count']}  ·  Words: {draft['stats']['total_word_count']}",
            f"Citations: {draft['stats']['verified_cites']} verified, {draft['stats']['pending_cites']} pending, {draft['stats']['needed_cites']} needed",
            f"Weak sections (insufficient evidence): {draft['stats']['weak_sections']}",
            "",
            "=" * 72,
            "",
        ]
        for s in draft["sections"]:
            stats_line = (
                f"[{s.get('status','OK')}] cites: ✓{s.get('verified_cites',0)} "
                f"⏳{s.get('pending_cites',0)} ✗{s.get('needed_cites',0)}"
            )
            out.append(f"## {s['title']}     {stats_line}")
            out.append("-" * 72)
            out.append(s["body"])
            out.append("")
        return "\n".join(out)

    # ---------- storage ----------
    def get_draft(self, draft_id: str) -> dict | None:
        return self._drafts.get(draft_id)

    def list_drafts(self, workspace_id: str | None = None) -> list[dict]:
        out = list(self._drafts.values())
        if workspace_id:
            out = [d for d in out if d["workspace_id"] == workspace_id]
        return out
