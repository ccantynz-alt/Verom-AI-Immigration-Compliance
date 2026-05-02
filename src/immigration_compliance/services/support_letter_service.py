"""Support Letter Generator + Bulk Letter Generation.

Companion to PetitionLetterService — drafts the support letters that go
into the petition packet:

  - employer_support       Employer's letter explaining the role + duties
                           + qualifications match (H-1B, L-1, O-1)
  - expert_opinion         Independent expert testifying to the
                           beneficiary's extraordinary ability (O-1, EB-1)
  - peer_recommendation    Peer/colleague letter (O-1, EB-1)
  - reference_letter       Professional reference (multiple visa types)
  - membership_attestation Association attesting outstanding-achievement
                           membership (O-1, EB-1)
  - critical_role          Letter from distinguished organization
                           explaining the beneficiary's critical role

Bulk generation: a single call produces multiple letters from the same
case data with variation in framing — different expert letters for
different criteria, multiple reference letters from different angles.

Same anti-hallucination discipline as the petition letter generator:
templated language with [VERIFIED] / [PENDING_VERIFICATION] /
[CITATION_NEEDED] markers; case-specific facts pulled from intake +
extracted documents."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Letter templates
# ---------------------------------------------------------------------------

LETTER_TEMPLATES: dict[str, dict[str, Any]] = {
    "employer_support": {
        "name": "Employer Support Letter",
        "applicable_visas": ["H-1B", "L-1", "L-1A", "O-1", "TN", "E-2", "H-2"],
        "from_role": "Employer / Petitioner",
        "min_pages": 2,
        "sections": ["company_introduction", "role_description", "duties_detail", "candidate_qualifications", "specialty_argument", "conclusion"],
        "subject_label": "{visa_type} Petition for {beneficiary_name}",
    },
    "expert_opinion": {
        "name": "Expert Opinion Letter",
        "applicable_visas": ["O-1", "O-1A", "O-1B", "EB-1A", "EB-1B", "EB-2-NIW"],
        "from_role": "Independent Expert in the Field",
        "min_pages": 3,
        "sections": ["expert_credentials", "field_overview", "criteria_addressed", "specific_contributions", "field_significance", "conclusion"],
        "subject_label": "Expert Opinion in Support of {beneficiary_name}",
        "criteria_focus_required": True,
    },
    "peer_recommendation": {
        "name": "Peer Recommendation Letter",
        "applicable_visas": ["O-1", "EB-1A", "EB-1B"],
        "from_role": "Peer / Colleague",
        "min_pages": 1,
        "sections": ["peer_introduction", "professional_relationship", "specific_collaborations", "assessment", "conclusion"],
        "subject_label": "Peer Recommendation for {beneficiary_name}",
    },
    "reference_letter": {
        "name": "Reference Letter",
        "applicable_visas": ["H-1B", "L-1", "O-1", "EB-1", "EB-2", "I-130"],
        "from_role": "Professional Reference",
        "min_pages": 1,
        "sections": ["reference_credentials", "relationship", "professional_observations", "endorsement"],
        "subject_label": "Reference for {beneficiary_name}",
    },
    "membership_attestation": {
        "name": "Membership Attestation Letter",
        "applicable_visas": ["O-1", "EB-1A", "EB-1B"],
        "from_role": "Association / Organization Officer",
        "min_pages": 1,
        "sections": ["organization_introduction", "membership_criteria", "beneficiary_membership", "significance"],
        "subject_label": "Attestation of Membership for {beneficiary_name}",
    },
    "critical_role": {
        "name": "Critical Role Letter",
        "applicable_visas": ["O-1", "EB-1A", "EB-1B"],
        "from_role": "Distinguished Organization Officer",
        "min_pages": 1,
        "sections": ["org_distinction", "beneficiary_role", "specific_contributions", "essential_nature"],
        "subject_label": "Critical Role Attestation for {beneficiary_name}",
    },
    "professor_endorsement": {
        "name": "Outstanding Researcher/Professor Endorsement",
        "applicable_visas": ["EB-1B"],
        "from_role": "Senior Faculty / Department Chair",
        "min_pages": 2,
        "sections": ["recommender_credentials", "academic_field_overview", "international_recognition", "research_contributions", "permanent_position_offer"],
        "subject_label": "Endorsement for {beneficiary_name}",
    },
}


# Citation markers (mirror petition_letter_service)
CITATION_VERIFIED = "[VERIFIED]"
CITATION_PENDING = "[PENDING_VERIFICATION]"
CITATION_NEEDED = "[CITATION_NEEDED]"
INSUFFICIENT_EVIDENCE = "[INSUFFICIENT_EVIDENCE]"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SupportLetterService:
    """Generate individual or bulk support letters."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
        document_intake: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._docs = document_intake
        self._letters: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_letter_kinds(visa_type: str | None = None) -> list[dict]:
        out = []
        for kid, spec in LETTER_TEMPLATES.items():
            if visa_type and visa_type not in spec.get("applicable_visas", []):
                continue
            out.append({
                "id": kid,
                "name": spec["name"],
                "from_role": spec["from_role"],
                "applicable_visas": spec["applicable_visas"],
                "section_count": len(spec["sections"]),
                "min_pages": spec["min_pages"],
            })
        return out

    @staticmethod
    def get_template(letter_kind: str) -> dict | None:
        return LETTER_TEMPLATES.get(letter_kind)

    # ---------- single letter generation ----------
    def generate(
        self,
        workspace_id: str,
        letter_kind: str,
        author_profile: dict | None = None,
        criterion_focus: str | None = None,
        custom_facts: dict | None = None,
    ) -> dict:
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")
        spec = LETTER_TEMPLATES.get(letter_kind)
        if spec is None:
            raise ValueError(f"Unknown letter kind: {letter_kind}")
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

        author = author_profile or {}
        facts = self._gather_facts(ws, answers, documents, custom_facts)
        sections = self._render_sections(letter_kind, spec, facts, author, criterion_focus)
        body = self._compose_body(letter_kind, spec, sections, facts, author)

        # Stats
        verified = body.count(CITATION_VERIFIED)
        pending = body.count(CITATION_PENDING)
        needed = body.count(CITATION_NEEDED)
        word_count = len(body.split())

        record = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "letter_kind": letter_kind,
            "letter_name": spec["name"],
            "from_role": spec["from_role"],
            "criterion_focus": criterion_focus,
            "author_profile": author,
            "facts": facts,
            "body": body,
            "sections": sections,
            "stats": {
                "word_count": word_count,
                "verified_cites": verified,
                "pending_cites": pending,
                "needed_cites": needed,
                "section_count": len(sections),
                "min_pages": spec["min_pages"],
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._letters[record["id"]] = record
        return record

    # ---------- bulk generation ----------
    def generate_bulk(
        self,
        workspace_id: str,
        plan: list[dict],
    ) -> dict:
        """Generate multiple letters in one call. `plan` is a list of:
            { "letter_kind": str, "author_profile": dict, "criterion_focus": str|None }
        Useful for petitions that need 5+ letters of different kinds."""
        results = []
        for item in plan:
            try:
                rec = self.generate(
                    workspace_id=workspace_id,
                    letter_kind=item["letter_kind"],
                    author_profile=item.get("author_profile"),
                    criterion_focus=item.get("criterion_focus"),
                    custom_facts=item.get("custom_facts"),
                )
                results.append({"status": "ok", "letter": rec})
            except Exception as e:
                results.append({"status": "error", "error": str(e), "request": item})

        return {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "total_requested": len(plan),
            "succeeded": sum(1 for r in results if r["status"] == "ok"),
            "failed": sum(1 for r in results if r["status"] == "error"),
            "results": results,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # ---------- factuals ----------
    @staticmethod
    def _gather_facts(ws: dict, answers: dict, documents: list[dict], custom: dict | None) -> dict:
        """Pull all the factual seeds the templates need from one place."""
        passport = next((d for d in documents if d.get("document_type") == "passport"), None)
        passport_extracted = (passport or {}).get("extracted", {}) if passport else {}
        first_name = answers.get("first_name") or ""
        last_name = answers.get("last_name") or ""
        full_name_extracted = passport_extracted.get("full_name") or f"{first_name} {last_name}".strip() or "[Beneficiary]"
        facts = {
            "beneficiary_name": full_name_extracted,
            "beneficiary_dob": passport_extracted.get("dob") or answers.get("dob"),
            "beneficiary_country": passport_extracted.get("nationality") or answers.get("country_of_birth"),
            "passport_number": passport_extracted.get("passport_number"),
            "visa_type": ws.get("visa_type"),
            "petitioner_name": answers.get("petitioner_name") or answers.get("petitioner_full_name"),
            "position_title": answers.get("position_title"),
            "position_duties_summary": answers.get("position_duties"),
            "wage_level": answers.get("wage_level"),
            "wage_offered": answers.get("wage_offered"),
            "has_us_masters": answers.get("us_masters_or_higher"),
            "has_bachelors": answers.get("has_bachelors_or_higher"),
            "current_status": answers.get("current_status_in_us"),
            "criteria_satisfied": [k for k, v in answers.items() if k.startswith("criteria_") and v],
        }
        if custom:
            facts.update(custom)
        return facts

    # ---------- section rendering ----------
    def _render_sections(
        self, letter_kind: str, spec: dict, facts: dict, author: dict, criterion_focus: str | None
    ) -> list[dict]:
        out = []
        for sid in spec["sections"]:
            method = getattr(self, f"_section_{sid}", None) or self._section_generic
            text = method(facts, author, letter_kind, criterion_focus)
            out.append({"id": sid, "title": sid.replace("_", " ").title(), "body": text})
        return out

    @staticmethod
    def _section_generic(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return f"[Section content for {kind} — case-specific facts go here.] {CITATION_NEEDED}"

    @staticmethod
    def _section_company_introduction(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{facts.get('petitioner_name','[Company]')} is a {author.get('industry','[industry]')} "
            f"company {author.get('company_description','engaged in [activities]')}. "
            f"The Company employs {author.get('employee_count','[#]')} individuals across "
            f"{author.get('locations','[locations]')}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_role_description(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"The Company is petitioning for {facts.get('beneficiary_name')} to fill the position of "
            f"{facts.get('position_title','[Position Title]')}. The position requires the application "
            f"of theoretical and practical knowledge in {author.get('field','[field]')}, satisfying "
            f"the specialty occupation standard under 8 C.F.R. § 214.2(h)(4) {CITATION_VERIFIED}."
        )

    @staticmethod
    def _section_duties_detail(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        duties = facts.get("position_duties_summary") or "[detailed duties list]"
        return (
            "The day-to-day duties of the position include:\n"
            f"  • {duties}\n"
            "These duties require sustained application of specialized knowledge, "
            f"and would not be performed by a person without the requisite credentials. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_candidate_qualifications(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        deg = "U.S. master's degree or higher" if facts.get("has_us_masters") else "U.S. bachelor's degree or its equivalent"
        return (
            f"{facts.get('beneficiary_name')} possesses {deg} in {author.get('degree_field','[field]')}, "
            f"directly aligned with the position's required body of knowledge. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_specialty_argument(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        wage_l = facts.get("wage_level")
        wage_addendum = ""
        if wage_l == "I":
            wage_addendum = (
                f"While the offered position is at Wage Level I, the duties require the application "
                f"of specialized theoretical knowledge irrespective of the DOL wage classification. {CITATION_PENDING}"
            )
        return (
            "The position is a specialty occupation under any of the four regulatory tests at "
            f"8 C.F.R. § 214.2(h)(4)(iii)(A) {CITATION_VERIFIED}: the position normally requires "
            "a bachelor's degree, the requirement is common in the industry, the petitioner consistently "
            f"requires the credential, and the duties are sufficiently specialized that the knowledge "
            f"is associated with degree-level study.\n{wage_addendum}"
        )

    @staticmethod
    def _section_expert_credentials(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"I, {author.get('name','[Expert Name]')}, am {author.get('title','[Title]')} at "
            f"{author.get('institution','[Institution]')}. I have served in the field of "
            f"{author.get('field','[field]')} for {author.get('years_in_field','[#]')} years, "
            f"during which I have authored {author.get('publication_count','[#]')} peer-reviewed "
            f"publications and served as a reviewer for {author.get('reviewer_role','[publications/grants/awards]')}. "
            f"{CITATION_PENDING}"
        )

    @staticmethod
    def _section_field_overview(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"The field of {author.get('field','[field]')} is characterized by [significant achievements]. "
            f"Practitioners in the top tier are recognized through {author.get('recognition_signals','[awards, publications, etc.]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_criteria_addressed(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        if criterion:
            return (
                f"This letter specifically addresses the {criterion.replace('criteria_', '').replace('_', ' ')} criterion. "
                f"In my expert assessment, {facts.get('beneficiary_name')}'s work meets and exceeds the "
                f"regulatory standard for this criterion. {CITATION_NEEDED}"
            )
        criteria = facts.get("criteria_satisfied") or []
        if not criteria:
            return (
                f"In my assessment, {facts.get('beneficiary_name')} satisfies multiple regulatory "
                f"criteria as detailed below. {CITATION_NEEDED}"
            )
        labels = ", ".join(c.replace("criteria_", "").replace("_", " ") for c in criteria)
        return (
            f"In my assessment, {facts.get('beneficiary_name')} satisfies the following regulatory "
            f"criteria: {labels}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_specific_contributions(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"Specifically, {facts.get('beneficiary_name')} has made the following contributions "
            f"that I personally recognize as significant:\n"
            f"  • [Contribution 1] {CITATION_NEEDED}\n"
            f"  • [Contribution 2] {CITATION_NEEDED}\n"
            f"  • [Contribution 3] {CITATION_NEEDED}\n"
        )

    @staticmethod
    def _section_field_significance(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"These contributions are not merely incremental — they have advanced the field's "
            f"understanding of [topic] in measurable ways. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_peer_introduction(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"I, {author.get('name','[Name]')}, am writing to recommend {facts.get('beneficiary_name')} "
            f"for {facts.get('visa_type')} classification. I am {author.get('title','[Title]')} at "
            f"{author.get('institution','[Institution]')}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_professional_relationship(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"I have known {facts.get('beneficiary_name')} for {author.get('relationship_years','[#]')} years "
            f"in a professional capacity at {author.get('shared_context','[shared context]')}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_specific_collaborations(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"During this time, we have collaborated on {author.get('collaboration_summary','[projects]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_assessment(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"In my professional assessment, {facts.get('beneficiary_name')} is among the top "
            f"practitioners in our field. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_reference_credentials(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"I, {author.get('name','[Name]')}, am {author.get('title','[Title]')} at "
            f"{author.get('institution','[Institution]')}. I have known {facts.get('beneficiary_name')} "
            f"in a {author.get('relationship_type','professional')} capacity for "
            f"{author.get('relationship_years','[#]')} years. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_relationship(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"My relationship with {facts.get('beneficiary_name')} is "
            f"{author.get('relationship_description','[describe]')}, providing me with direct "
            f"observation of their work and character."
        )

    @staticmethod
    def _section_professional_observations(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"I have personally observed {facts.get('beneficiary_name')} demonstrate "
            f"{author.get('observed_skills','[skills/qualities]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_endorsement(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"On the basis of my direct knowledge, I endorse {facts.get('beneficiary_name')} "
            f"without reservation."
        )

    @staticmethod
    def _section_organization_introduction(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{author.get('organization_name','[Organization]')} is "
            f"{author.get('organization_description','[description]')}. The organization is recognized "
            f"in the field for {author.get('recognition','[reasons]')}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_membership_criteria(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"Membership in our organization requires {author.get('membership_criteria','[criteria]')}, "
            f"reviewed by a panel of established members. Mere educational achievement is not sufficient. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_beneficiary_membership(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{facts.get('beneficiary_name')} was admitted to membership in {author.get('admission_year','[year]')} "
            f"on the basis of {author.get('admission_basis','[criteria]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_significance(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"This membership signifies recognition by peers as having achieved a level of "
            f"competence and contribution that distinguishes the beneficiary in the field. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_org_distinction(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{author.get('organization_name','[Organization]')} is recognized as a distinguished "
            f"organization in {author.get('field','[field]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_beneficiary_role(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{facts.get('beneficiary_name')} has served at our organization as "
            f"{author.get('role','[role]')} since {author.get('start_date','[date]')}. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_essential_nature(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"This role has been essential — not merely contributing but materially shaping the "
            f"organization's {author.get('shaped_outcome','[outcome]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_recommender_credentials(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return SupportLetterService._section_expert_credentials(facts, author, kind, criterion)

    @staticmethod
    def _section_academic_field_overview(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"The academic field of {author.get('field','[field]')} requires sustained scholarly "
            f"contribution recognized through peer-reviewed publication, citation, and conference "
            f"presentation. {CITATION_PENDING}"
        )

    @staticmethod
    def _section_international_recognition(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{facts.get('beneficiary_name')} is recognized internationally — as evidenced by "
            f"citation count, invited talks, and peer-reviewer roles at top venues. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_research_contributions(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"Specific research contributions include {author.get('research_contributions','[contributions]')}. {CITATION_NEEDED}"
        )

    @staticmethod
    def _section_permanent_position_offer(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"{author.get('institution','[Institution]')} has offered {facts.get('beneficiary_name')} "
            f"a permanent research/teaching position, satisfying the EB-1B requirement under "
            f"8 C.F.R. § 204.5(i) {CITATION_VERIFIED}."
        )

    @staticmethod
    def _section_conclusion(facts: dict, author: dict, kind: str, criterion: str | None) -> str:
        return (
            f"For all of the foregoing reasons, I respectfully and without reservation support "
            f"the petition for {facts.get('beneficiary_name')}'s {facts.get('visa_type')} classification.\n\n"
            f"Sincerely,\n\n[Signature]\n{author.get('name','[Name]')}\n"
            f"{author.get('title','[Title]')}\n{author.get('institution','[Institution]')}\n"
        )

    # ---------- composition ----------
    @staticmethod
    def _compose_body(letter_kind: str, spec: dict, sections: list[dict], facts: dict, author: dict) -> str:
        today = date.today().isoformat()
        head = (
            f"{author.get('name','[Author Name]')}\n"
            f"{author.get('title','[Title]')}\n"
            f"{author.get('institution','[Institution]')}\n"
            f"{author.get('address','[Address]')}\n\n"
            f"{today}\n\n"
            f"USCIS\n[Service Center Address]\n\n"
            f"Re: {spec['subject_label'].format(visa_type=facts.get('visa_type','[Visa]'), beneficiary_name=facts.get('beneficiary_name','[Beneficiary]'))}\n\n"
            "Dear USCIS Officer:\n\n"
        )
        body = head
        for s in sections:
            body += s["body"] + "\n\n"
        return body

    # ---------- output formats ----------
    @staticmethod
    def render_text(record: dict) -> str:
        return record["body"]

    @staticmethod
    def render_review_text(record: dict) -> str:
        out = [
            f"# {record['letter_name']}",
            f"Workspace: {record['workspace_id']}",
            f"From role: {record['from_role']}",
            f"Words: {record['stats']['word_count']}  ·  Sections: {record['stats']['section_count']}",
            f"Citations: ✓{record['stats']['verified_cites']} ⏳{record['stats']['pending_cites']} ✗{record['stats']['needed_cites']}",
            "",
            "=" * 72, "",
            record["body"],
        ]
        return "\n".join(out)

    # ---------- storage ----------
    def get_letter(self, letter_id: str) -> dict | None:
        return self._letters.get(letter_id)

    def list_letters(self, workspace_id: str | None = None, letter_kind: str | None = None) -> list[dict]:
        out = list(self._letters.values())
        if workspace_id:
            out = [l for l in out if l["workspace_id"] == workspace_id]
        if letter_kind:
            out = [l for l in out if l["letter_kind"] == letter_kind]
        return out
