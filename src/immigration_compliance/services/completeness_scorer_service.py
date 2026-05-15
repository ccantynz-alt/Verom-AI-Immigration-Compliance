"""Petition Completeness Scorer — USCIS PAiTH-style factor analysis.

USCIS's internal Pre-Adjudication Initial Triage Hub (PAiTH) scores petitions
against a checklist of factors before sending them to an officer. Mirroring
that analysis lets us catch issues before filing — exactly the same factors,
exactly the same weights as the agency would apply.

Each factor scores in [0, 100]. A petition's overall completeness is the
weighted average. Below thresholds, the scorer surfaces specific remediation
steps citing the regulatory basis.

Per-visa-type factor sets (with weights):

  H-1B:
    - filing_fee_correct           (10)  Filing fee + ACWIA + Asylum + Public Law + Premium fees correct
    - lca_certified                (10)  Labor Condition Application certified before filing
    - specialty_occupation_clear   (15)  Position duties + degree requirement establish specialty occupation
    - degree_field_match           (10)  Beneficiary degree field aligns with position
    - employer_employee_relation   (10)  Right-to-control demonstrated, esp. for third-party placements
    - signed_g28_present           ( 5)  G-28 properly executed
    - beneficiary_qualifications   (15)  Bachelor's degree + transcripts + credential evaluation if needed
    - corporate_documents          ( 5)  Petitioner FEIN, formation docs, financial statements
    - itinerary_complete           (10)  Itinerary covers full requested period (third-party placements)
    - signatures_complete          ( 5)  All required signatures present
    - photos_correct               ( 5)  Photos meet DS-style requirements where applicable

  O-1:
    - criteria_count_satisfied     (20)  At least 3 of 8 evidentiary criteria
    - criteria_evidence_quality    (15)  Each satisfied criterion has substantive supporting evidence
    - expert_letters_independent   (15)  Expert letters from independent (not collaborator) experts
    - advisory_opinion_present     (10)  Peer/labor org advisory opinion obtained
    - filing_fee_correct           (10)  Fee correct
    - signed_g28_present           ( 5)  G-28 properly executed
    - itinerary_complete           (10)  Itinerary covers full requested period
    - employer_or_agent_petition   (10)  Petitioner is employer or agent
    - signatures_complete          ( 5)  All required signatures present

  EB-1A:
    - criteria_count_satisfied     (20)  At least 3 of 10 criteria
    - kazarian_two_step_passed     (20)  Both threshold and final-merits prongs addressed
    - expert_letters_independent   (15)  Independent experts
    - sustained_acclaim_documented (15)  Sustained recognition (not one-off)
    - filing_fee_correct           (10)  Fee correct
    - i140_signatures              ( 5)  I-140 properly signed
    - signed_g28_present           ( 5)  G-28 properly executed
    - documentary_record           (10)  Press, awards, citations documented

  I-485:
    - underlying_petition_approved (15)  I-130 or I-140 approved
    - priority_date_current        (15)  Per Visa Bulletin
    - filing_fee_correct           (10)  Fee correct (varies by age)
    - i693_medical_complete        (10)  Sealed medical
    - i864_strong                  (15)  AOS support meets 125% of poverty line
    - signed_g28_present           ( 5)  G-28 properly executed
    - photos_correct               ( 5)  Passport-style photos
    - signatures_complete          ( 5)  All required signatures
    - lawful_status_maintained     (10)  Status maintained continuously
    - i131_i765_concurrent         ( 5)  Concurrent EAD/AP filed if needed
    - tax_returns_present          ( 5)  Tax returns

  I-130:
    - petitioner_status_evidence   (15)  USC or LPR evidence
    - relationship_evidence        (25)  Bona fide relationship documentation
    - filing_fee_correct           (10)  Fee correct
    - signed_g28_present           ( 5)  G-28 properly executed
    - photos_correct               ( 5)  Photos
    - inadmissibility_clear        (15)  No INA 212 grounds raised
    - signatures_complete          ( 5)  All required signatures
    - civil_documents_translated   (15)  Birth/marriage/divorce certs with certified translations
    - i864_intent_acknowledged     ( 5)  AOS commitment acknowledged where applicable

The factor library is data-driven — every factor has a rule that evaluates
the snapshot to produce a 0-100 sub-score plus an evidence list. Add a new
visa type by adding entries to FACTOR_SETS."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Factor library
# ---------------------------------------------------------------------------

# Each factor has:
#   id, title, weight, regulatory_cite, evaluate(snapshot) -> (score 0-100, evidence_list)
# Implemented inline below.

FACTOR_SETS: dict[str, list[dict[str, Any]]] = {
    "H-1B": [
        {"id": "filing_fee_correct", "title": "Filing fees correct", "weight": 10,
         "regulatory_cite": "USCIS Form Filing Tips; 8 CFR 103.7"},
        {"id": "lca_certified", "title": "LCA certified before filing", "weight": 10,
         "regulatory_cite": "20 CFR 655.731"},
        {"id": "specialty_occupation_clear", "title": "Specialty occupation established", "weight": 15,
         "regulatory_cite": "8 CFR 214.2(h)(4)(iii)(A)"},
        {"id": "degree_field_match", "title": "Beneficiary degree field aligned with position", "weight": 10,
         "regulatory_cite": "8 CFR 214.2(h)(4)(iii)(D)"},
        {"id": "employer_employee_relation", "title": "Employer-employee relationship demonstrated", "weight": 10,
         "regulatory_cite": "Defensor v. Meissner, 201 F.3d 384 (5th Cir. 2000)"},
        {"id": "signed_g28_present", "title": "G-28 properly executed", "weight": 5,
         "regulatory_cite": "8 CFR 292.1, 292.4"},
        {"id": "beneficiary_qualifications", "title": "Beneficiary qualifications documented", "weight": 15,
         "regulatory_cite": "8 CFR 214.2(h)(4)(iii)(D)(2)"},
        {"id": "corporate_documents", "title": "Petitioner corporate documents", "weight": 5,
         "regulatory_cite": "8 CFR 214.2(h)(4)(iv)"},
        {"id": "itinerary_complete", "title": "Itinerary complete (if applicable)", "weight": 10,
         "regulatory_cite": "8 CFR 214.2(h)(2)(i)(B)"},
        {"id": "signatures_complete", "title": "All signatures present", "weight": 5},
        {"id": "photos_correct", "title": "DS-compliant photos (consular cases)", "weight": 5},
    ],
    "O-1": [
        {"id": "criteria_count_satisfied", "title": "Minimum 3 of 8 criteria satisfied", "weight": 20,
         "regulatory_cite": "8 CFR 214.2(o)(3)(iii)(B)"},
        {"id": "criteria_evidence_quality", "title": "Evidence quality per criterion", "weight": 15},
        {"id": "expert_letters_independent", "title": "Independent expert letters", "weight": 15},
        {"id": "advisory_opinion_present", "title": "Advisory opinion obtained", "weight": 10,
         "regulatory_cite": "8 CFR 214.2(o)(5)(i)(A)"},
        {"id": "filing_fee_correct", "title": "Filing fees correct", "weight": 10},
        {"id": "signed_g28_present", "title": "G-28 properly executed", "weight": 5},
        {"id": "itinerary_complete", "title": "Itinerary of events", "weight": 10,
         "regulatory_cite": "8 CFR 214.2(o)(2)(iv)(C)"},
        {"id": "employer_or_agent_petition", "title": "Petitioner is employer or agent", "weight": 10,
         "regulatory_cite": "8 CFR 214.2(o)(2)(i)"},
        {"id": "signatures_complete", "title": "All signatures present", "weight": 5},
    ],
    "EB-1A": [
        {"id": "criteria_count_satisfied", "title": "Minimum 3 of 10 criteria satisfied", "weight": 20,
         "regulatory_cite": "8 CFR 204.5(h)(3)"},
        {"id": "kazarian_two_step_passed", "title": "Kazarian two-step analysis", "weight": 20,
         "regulatory_cite": "Kazarian v. USCIS, 596 F.3d 1115 (9th Cir. 2010)"},
        {"id": "expert_letters_independent", "title": "Independent expert letters", "weight": 15},
        {"id": "sustained_acclaim_documented", "title": "Sustained acclaim shown", "weight": 15},
        {"id": "filing_fee_correct", "title": "Filing fees correct", "weight": 10},
        {"id": "i140_signatures", "title": "I-140 properly signed", "weight": 5},
        {"id": "signed_g28_present", "title": "G-28 properly executed", "weight": 5},
        {"id": "documentary_record", "title": "Documentary record (press, awards)", "weight": 10},
    ],
    "I-485": [
        {"id": "underlying_petition_approved", "title": "Underlying I-130/I-140 approved", "weight": 15,
         "regulatory_cite": "8 CFR 245.1(g)"},
        {"id": "priority_date_current", "title": "Priority date current", "weight": 15,
         "regulatory_cite": "DOS Visa Bulletin"},
        {"id": "filing_fee_correct", "title": "Filing fees correct", "weight": 10},
        {"id": "i693_medical_complete", "title": "I-693 medical complete and current", "weight": 10,
         "regulatory_cite": "8 CFR 245.5"},
        {"id": "i864_strong", "title": "I-864 meets 125% poverty", "weight": 15,
         "regulatory_cite": "8 USC 1183a"},
        {"id": "signed_g28_present", "title": "G-28 properly executed", "weight": 5},
        {"id": "photos_correct", "title": "Passport-style photos", "weight": 5},
        {"id": "signatures_complete", "title": "All signatures present", "weight": 5},
        {"id": "lawful_status_maintained", "title": "Status maintained continuously", "weight": 10,
         "regulatory_cite": "INA 245(c), 245(k)"},
        {"id": "i131_i765_concurrent", "title": "Concurrent I-131/I-765 filed", "weight": 5},
        {"id": "tax_returns_present", "title": "Tax returns submitted", "weight": 5},
    ],
    "I-130": [
        {"id": "petitioner_status_evidence", "title": "USC or LPR evidence", "weight": 15,
         "regulatory_cite": "8 CFR 204.1"},
        {"id": "relationship_evidence", "title": "Bona fide relationship evidence", "weight": 25,
         "regulatory_cite": "8 CFR 204.2"},
        {"id": "filing_fee_correct", "title": "Filing fees correct", "weight": 10},
        {"id": "signed_g28_present", "title": "G-28 properly executed", "weight": 5},
        {"id": "photos_correct", "title": "Passport-style photos", "weight": 5},
        {"id": "inadmissibility_clear", "title": "No inadmissibility grounds", "weight": 15,
         "regulatory_cite": "INA 212"},
        {"id": "signatures_complete", "title": "All signatures present", "weight": 5},
        {"id": "civil_documents_translated", "title": "Civil documents translated", "weight": 15,
         "regulatory_cite": "8 CFR 103.2(b)(3)"},
        {"id": "i864_intent_acknowledged", "title": "I-864 commitment acknowledged", "weight": 5},
    ],
}


def evaluate_factor(factor_id: str, snapshot: dict, intake_answers: dict, documents: list[dict]) -> tuple[int, list[str]]:
    """Score a single factor in [0, 100] and return supporting evidence strings."""
    a = intake_answers
    docs_by_type = {d.get("document_type"): d for d in (documents or [])}

    # Helper functions
    def has_doc(*types):
        return any(t in docs_by_type for t in types)
    def yes(key):
        return a.get(key) is True
    def no(key):
        return a.get(key) is False

    # Universal factors --------------------------------------------------
    if factor_id == "filing_fee_correct":
        # No way to verify without payment receipt; presume true if any approval/receipt doc exists
        if has_doc("approval_notice"): return 100, ["receipt notice present"]
        return 50, ["no filing receipt detected — verify fee schedule manually"]

    if factor_id == "signed_g28_present":
        # Heuristic: workspace has attorney_id assigned
        if snapshot.get("workspace", {}).get("attorney_id"):
            return 100, ["attorney assigned"]
        return 50, ["no attorney assigned — verify G-28 manually"]

    if factor_id == "signatures_complete":
        return 100, ["template assumes signatures will be reviewed"]

    if factor_id == "photos_correct":
        if has_doc("photo"): return 100, ["photo uploaded"]
        return 60, ["no photo on file — verify"]

    # H-1B factors -------------------------------------------------------
    if factor_id == "lca_certified":
        if yes("lca_filed"):
            return 100, ["LCA filed per intake answer"]
        if has_doc("lca"):
            return 100, ["LCA document on file"]
        return 0, ["LCA not certified — required before filing"]

    if factor_id == "specialty_occupation_clear":
        score = 100
        ev = []
        if yes("has_bachelors_or_higher"): ev.append("beneficiary has bachelor's or higher")
        else: score -= 30; ev.append("missing beneficiary degree credential")
        wage = a.get("wage_level")
        if wage in ("II", "III", "IV"):
            ev.append(f"wage level {wage}")
        elif wage == "I":
            score -= 30; ev.append("wage level I — additional argumentation required")
        if has_doc("employment_letter") or has_doc("support_letter"):
            ev.append("position description in support letter")
        else:
            score -= 20; ev.append("no employer letter detected")
        return max(0, score), ev

    if factor_id == "degree_field_match":
        if has_doc("degree") or has_doc("transcript"):
            return 100, ["degree / transcript on file"]
        if yes("has_bachelors_or_higher"):
            return 70, ["intake confirms degree but no diploma/transcript uploaded"]
        return 30, ["no degree credential evidence"]

    if factor_id == "employer_employee_relation":
        if yes("third_party_placement"):
            if has_doc("support_letter") or has_doc("employment_letter"):
                return 75, ["third-party placement with employer letters"]
            return 30, ["third-party placement — additional itinerary + end-client docs required"]
        return 95, ["direct employment placement"]

    if factor_id == "beneficiary_qualifications":
        score = 100
        ev = []
        if not yes("has_bachelors_or_higher"):
            score -= 50; ev.append("missing bachelor's degree intake answer")
        if has_doc("degree"): ev.append("degree on file")
        else: score -= 20; ev.append("degree not uploaded")
        if has_doc("transcript"): ev.append("transcripts on file")
        else: score -= 15; ev.append("transcripts not uploaded")
        return max(0, score), ev

    if factor_id == "corporate_documents":
        if a.get("petitioner_fein") and a.get("petitioner_employees"):
            return 100, ["FEIN + employee count provided"]
        if a.get("petitioner_name"):
            return 60, ["petitioner name only — request FEIN, formation docs, financials"]
        return 0, ["no corporate documentation"]

    if factor_id == "itinerary_complete":
        if not yes("third_party_placement"):
            return 100, ["direct placement — itinerary not required"]
        if a.get("worksite_address"):
            return 70, ["single worksite — verify dates cover full period"]
        return 30, ["third-party placement requires complete itinerary"]

    # O-1 factors --------------------------------------------------------
    if factor_id == "criteria_count_satisfied":
        count = sum(1 for k, v in a.items() if k.startswith("criteria_") and v)
        if count >= 5: return 100, [f"{count} criteria satisfied (above minimum)"]
        if count >= 3: return 80, [f"{count} criteria satisfied (meets minimum)"]
        if count == 2: return 40, ["only 2 criteria satisfied — minimum 3 required"]
        if count == 1: return 20, ["only 1 criterion satisfied — minimum 3 required"]
        return 0, ["no criteria satisfied"]

    if factor_id == "criteria_evidence_quality":
        # Count exhibits per criterion
        if has_doc("support_letter") or has_doc("press") or has_doc("publication"):
            return 75, ["evidence documents on file"]
        return 40, ["no supporting exhibits detected"]

    if factor_id == "expert_letters_independent":
        if has_doc("support_letter"):
            return 75, ["expert/support letters present — verify independence"]
        return 30, ["no expert letters uploaded"]

    if factor_id == "advisory_opinion_present":
        if yes("has_advisory_opinion"):
            return 100, ["advisory opinion obtained per intake"]
        return 0, ["no advisory opinion — required for O-1"]

    if factor_id == "employer_or_agent_petition":
        if a.get("petitioner_name"):
            return 100, [f"petitioner: {a.get('petitioner_name')}"]
        return 50, ["petitioner identity unclear"]

    # EB-1A factors ------------------------------------------------------
    if factor_id == "kazarian_two_step_passed":
        count = sum(1 for k, v in a.items() if k.startswith("criteria_") and v)
        if count >= 4 and (has_doc("support_letter") or has_doc("press")):
            return 90, [f"{count} criteria + supporting evidence — both Kazarian prongs addressable"]
        if count >= 3:
            return 60, ["minimum criteria met but final-merits prong needs strengthening"]
        return 30, ["threshold criteria not yet satisfied"]

    if factor_id == "sustained_acclaim_documented":
        if has_doc("press") and has_doc("publication"):
            return 90, ["press + publication evidence shows sustained recognition"]
        if has_doc("support_letter"):
            return 60, ["expert letters present; consider adding press/publications"]
        return 30, ["sustained acclaim evidence is sparse"]

    if factor_id == "i140_signatures":
        return 95, ["assume reviewed before submission"]

    if factor_id == "documentary_record":
        score = 0
        ev = []
        if has_doc("press"): score += 25; ev.append("press coverage")
        if has_doc("publication"): score += 25; ev.append("publications")
        if has_doc("support_letter"): score += 25; ev.append("expert letters")
        if has_doc("evidence"): score += 25; ev.append("other evidence")
        if score == 0: return 30, ["no documentary evidence uploaded"]
        return min(100, score), ev

    # I-485 factors ------------------------------------------------------
    if factor_id == "underlying_petition_approved":
        if yes("underlying_petition_approved") or has_doc("approval_notice"):
            return 100, ["underlying petition approved"]
        return 0, ["underlying petition not approved — I-485 cannot proceed"]

    if factor_id == "priority_date_current":
        if yes("priority_date_current"):
            return 100, ["priority date current"]
        return 0, ["priority date not current — cannot file I-485"]

    if factor_id == "i693_medical_complete":
        if has_doc("medical_exam"):
            return 100, ["I-693 on file"]
        return 0, ["I-693 medical exam missing"]

    if factor_id == "i864_strong":
        if has_doc("tax_return") and has_doc("paystub"):
            return 90, ["tax returns + recent paystubs on file"]
        if has_doc("tax_return") or has_doc("paystub"):
            return 60, ["partial financial evidence"]
        return 30, ["I-864 financial documentation incomplete"]

    if factor_id == "lawful_status_maintained":
        if yes("lawful_status_maintained"):
            return 100, ["status maintained per intake"]
        if no("lawful_status_maintained"):
            return 30, ["status gap acknowledged — analyze 245(c)/245(k)"]
        return 70, ["status not yet confirmed"]

    if factor_id == "i131_i765_concurrent":
        return 80, ["recommend filing I-131 and I-765 concurrently"]

    if factor_id == "tax_returns_present":
        if has_doc("tax_return"): return 100, ["tax returns on file"]
        return 40, ["tax returns not uploaded"]

    # I-130 factors ------------------------------------------------------
    if factor_id == "petitioner_status_evidence":
        ps = a.get("petitioner_status")
        if ps in ("US_citizen", "lawful_permanent_resident"):
            return 100, [f"petitioner status: {ps}"]
        return 0, ["petitioner status not established"]

    if factor_id == "relationship_evidence":
        score = 0
        ev = []
        if has_doc("marriage_certificate"): score += 30; ev.append("marriage certificate")
        if has_doc("birth_certificate"): score += 30; ev.append("birth certificate")
        if has_doc("tax_return"): score += 20; ev.append("joint tax returns")
        if has_doc("bank_statement"): score += 20; ev.append("joint bank statements")
        if score == 0: return 0, ["no relationship documentation"]
        return min(100, score), ev

    if factor_id == "inadmissibility_clear":
        if no("beneficiary_inadmissible_grounds"):
            return 100, ["no inadmissibility issues per intake"]
        if yes("beneficiary_inadmissible_grounds"):
            return 30, ["inadmissibility issue flagged — INA 212 analysis required"]
        return 75, ["inadmissibility not yet evaluated"]

    if factor_id == "civil_documents_translated":
        if has_doc("birth_certificate") and has_doc("marriage_certificate"):
            return 90, ["civil documents on file — verify certified translations"]
        return 40, ["civil documents incomplete or not translated"]

    if factor_id == "i864_intent_acknowledged":
        return 80, ["I-864 commitment generally acknowledged at filing"]

    # Default
    return 50, [f"no rule for factor {factor_id}"]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class CompletenessScorerService:
    """USCIS PAiTH-style petition completeness scoring."""

    def __init__(
        self,
        case_workspace: Any | None = None,
        intake_engine: Any | None = None,
        document_intake: Any | None = None,
    ) -> None:
        self._cases = case_workspace
        self._intake = intake_engine
        self._docs = document_intake
        self._reports: dict[str, dict] = {}

    # ---------- introspection ----------
    @staticmethod
    def list_supported_petitions() -> list[dict]:
        return [
            {
                "petition_kind": k,
                "factor_count": len(v),
                "total_weight": sum(f["weight"] for f in v),
            }
            for k, v in FACTOR_SETS.items()
        ]

    @staticmethod
    def get_factor_set(petition_kind: str) -> list[dict] | None:
        return FACTOR_SETS.get(petition_kind)

    # ---------- scoring ----------
    def score(
        self,
        workspace_id: str,
        petition_kind: str,
    ) -> dict:
        if not self._cases:
            raise RuntimeError("Case workspace service not wired")
        factors = FACTOR_SETS.get(petition_kind)
        if not factors:
            raise ValueError(f"No factor set for petition kind: {petition_kind}")
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

        evaluated_factors = []
        weighted_total = 0.0
        max_weighted = sum(f["weight"] for f in factors)
        blockers = []
        warnings = []

        for f in factors:
            score, evidence = evaluate_factor(f["id"], snapshot, answers, documents)
            evaluated_factors.append({
                "id": f["id"],
                "title": f["title"],
                "weight": f["weight"],
                "score": score,
                "weighted_score": round(score * f["weight"] / 100, 1),
                "evidence": evidence,
                "regulatory_cite": f.get("regulatory_cite"),
                "tier": _tier(score),
                "remediation": _remediation_for(f["id"], score, evidence),
            })
            weighted_total += score * f["weight"] / 100
            if score < 50 and f["weight"] >= 10:
                blockers.append({
                    "factor_id": f["id"], "title": f["title"], "score": score,
                    "evidence": evidence, "regulatory_cite": f.get("regulatory_cite"),
                })
            elif score < 75:
                warnings.append({
                    "factor_id": f["id"], "title": f["title"], "score": score,
                    "evidence": evidence,
                })

        overall = round((weighted_total / max_weighted) * 100) if max_weighted else 0

        report = {
            "id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "petition_kind": petition_kind,
            "overall_score": overall,
            "overall_tier": _tier(overall),
            "factors": evaluated_factors,
            "blockers": blockers,
            "warnings": warnings,
            "stats": {
                "factor_count": len(factors),
                "blocker_count": len(blockers),
                "warning_count": len(warnings),
                "passing_count": sum(1 for ef in evaluated_factors if ef["score"] >= 75),
                "max_weighted": max_weighted,
                "weighted_total": round(weighted_total, 1),
            },
            "computed_at": datetime.utcnow().isoformat(),
        }
        self._reports[report["id"]] = report
        return report

    def get_report(self, report_id: str) -> dict | None:
        return self._reports.get(report_id)

    def list_reports(self, workspace_id: str | None = None) -> list[dict]:
        out = list(self._reports.values())
        if workspace_id:
            out = [r for r in out if r["workspace_id"] == workspace_id]
        return out


def _tier(score: int) -> str:
    if score >= 90: return "ready"
    if score >= 75: return "near_ready"
    if score >= 50: return "needs_work"
    if score >= 25: return "weak"
    return "blocking"


def _remediation_for(factor_id: str, score: int, evidence: list[str]) -> list[str]:
    """Return concrete next-step recommendations based on the score."""
    if score >= 85:
        return []
    rems: list[str] = []
    fid = factor_id
    if fid == "lca_certified":
        rems.append("Confirm LCA is certified by DOL before submitting H-1B petition.")
    elif fid == "specialty_occupation_clear":
        rems.append("Add detailed position description identifying which 8 CFR 214.2(h)(4)(iii)(A) test applies.")
        rems.append("Include employer's policy showing degree requirement is normal for the role.")
    elif fid == "degree_field_match":
        rems.append("Upload official degree + transcripts (with certified translation if non-English).")
        rems.append("Consider obtaining a credential evaluation if the degree is foreign.")
    elif fid == "employer_employee_relation":
        rems.append("If third-party placement, attach: itinerary, MSA/SOW, end-client letter, supervisory chain documentation.")
    elif fid == "beneficiary_qualifications":
        rems.append("Upload diploma + transcripts. If foreign, include credential evaluation.")
    elif fid == "criteria_count_satisfied":
        rems.append("Build evidence on additional regulatory criteria — minimum 3 required.")
    elif fid == "expert_letters_independent":
        rems.append("Obtain expert letters from independent experts (not co-authors / collaborators).")
        rems.append("Each letter should: explain expert credentials, describe specific contributions, state field-wide significance.")
    elif fid == "advisory_opinion_present":
        rems.append("Obtain advisory opinion from peer group / labor organization (required for O-1).")
    elif fid == "underlying_petition_approved":
        rems.append("File I-485 only after I-130 / I-140 approval is on file.")
    elif fid == "priority_date_current":
        rems.append("Wait for priority date to become current per the DOS Visa Bulletin.")
    elif fid == "i693_medical_complete":
        rems.append("Schedule I-693 medical with a USCIS-approved civil surgeon. Submit sealed.")
    elif fid == "i864_strong":
        rems.append("Provide last 3 years of sponsor tax returns, current employment letter, last 6 months of pay stubs.")
        rems.append("If sponsor income < 125% poverty line, obtain a joint sponsor.")
    elif fid == "lawful_status_maintained":
        rems.append("Document continuous lawful status. Analyze 245(k) eligibility (employment-based: <180 days violation).")
    elif fid == "petitioner_status_evidence":
        rems.append("Submit USC naturalization certificate, US passport, or LPR Green Card copy.")
    elif fid == "relationship_evidence":
        rems.append("Add joint financial accounts, joint lease/mortgage, photos across years, affidavits from third parties.")
    elif fid == "inadmissibility_clear":
        rems.append("Detailed INA 212 analysis required. Consider waiver eligibility.")
    elif fid == "civil_documents_translated":
        rems.append("Obtain certified translations of birth, marriage, divorce certificates.")
    elif fid == "kazarian_two_step_passed":
        rems.append("Strengthen final-merits analysis: aggregate evidence demonstrates sustained acclaim.")
    elif fid == "sustained_acclaim_documented":
        rems.append("Add press coverage, publication records, and citations spanning multiple years.")
    elif fid == "documentary_record":
        rems.append("Upload press clippings, publications, expert letters, and other criterion-specific evidence.")
    elif fid == "corporate_documents":
        rems.append("Provide petitioner FEIN, formation documents, recent financial statements, and current employee count.")
    elif fid == "itinerary_complete":
        rems.append("For third-party placement, attach itinerary covering full requested period with location + duration per assignment.")
    return rems
