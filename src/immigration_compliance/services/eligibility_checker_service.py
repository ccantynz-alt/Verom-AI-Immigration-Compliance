"""Boundless-Killer Eligibility Checker — fast, ungated visa qualification tool.

Public landing-page tool that answers "Will I qualify?" in under 90 seconds with
no signup. Returns a ranked list of visa pathways the applicant likely qualifies
for, with confidence scores and friction-free routing into the full intake.

Strategic value:
  - Top-of-funnel SEO play (each visa type gets its own ungated answer page)
  - Routes qualified applicants to attorney match without losing them to sign-up
  - Disqualifies obvious mismatches with helpful alternatives instead of dead ends

The decision tree is rules-based and explainable. Each pathway has a tight set
of binary disqualifiers and 3-5 strength factors. The tool is intentionally
narrower than the full IntakeEngine — the full intake is the next step after
this one, not its replacement.

Public API: no auth required. Output is shareable as a URL with answer hash.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Decision tree per visa pathway
# ---------------------------------------------------------------------------

# Each pathway: question_id → question definition
# Disqualifier questions: failing answer auto-rejects
# Strength factors: contribute to confidence score (0-100)

PATHWAYS: dict[str, dict[str, Any]] = {
    "H-1B": {
        "name": "H-1B Specialty Occupation",
        "description": "Employer-sponsored visa for specialty occupations requiring a bachelor's degree or higher.",
        "country": "US",
        "questions": [
            {"id": "has_bachelors", "label": "Do you hold a bachelor's degree or its equivalent?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "has_us_offer", "label": "Do you have a written job offer from a U.S. employer?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "specialty_field", "label": "Is your degree in a field directly related to the offered position?",
             "type": "boolean", "weight": 20},
            {"id": "us_masters", "label": "Do you hold a U.S. master's degree?",
             "type": "boolean", "weight": 15},
            {"id": "selected_lottery", "label": "Has your employer been selected in the H-1B lottery (or are they cap-exempt)?",
             "type": "boolean", "weight": 15, "disqualifier_if_explicit_no": True},
        ],
        "alternatives_on_disqualify": ["O-1", "L-1", "TN", "F-1_OPT"],
    },
    "O-1": {
        "name": "O-1 Extraordinary Ability",
        "description": "For individuals with extraordinary ability in sciences, arts, education, business, or athletics. No annual cap.",
        "country": "US",
        "questions": [
            {"id": "national_recognition", "label": "Have you been recognized nationally or internationally in your field?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "has_us_employer_or_agent", "label": "Do you have a U.S. employer or agent?",
             "type": "boolean", "weight": 20, "disqualifier_if": False},
            {"id": "criteria_count", "label": "How many of these apply: awards, association memberships, press, judging, original contributions, publications, critical role, high salary?",
             "type": "select", "options": ["0-2", "3-4", "5+"], "weight": 30,
             "disqualifier_if": "0-2"},
            {"id": "expert_letters_available", "label": "Can you obtain 5+ letters from independent experts in your field?",
             "type": "boolean", "weight": 15},
            {"id": "advisory_opinion_obtainable", "label": "Can you obtain an advisory opinion from a peer group or labor org?",
             "type": "boolean", "weight": 10},
        ],
        "alternatives_on_disqualify": ["EB-2-NIW", "H-1B"],
    },
    "EB-1A": {
        "name": "EB-1A Extraordinary Ability (Green Card)",
        "description": "Permanent residence for individuals with extraordinary ability. Self-petition, no employer needed.",
        "country": "US",
        "questions": [
            {"id": "extraordinary_ability", "label": "Are you among the top of your field, with sustained acclaim?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
            {"id": "criteria_count", "label": "How many of these apply: awards, memberships, press, judging, original contributions, scholarly articles, exhibitions, critical role, high salary, commercial success?",
             "type": "select", "options": ["0-2", "3", "4-6", "7+"], "weight": 35,
             "disqualifier_if": "0-2"},
            {"id": "us_intent", "label": "Do you intend to continue working in your field in the U.S.?",
             "type": "boolean", "weight": 15, "disqualifier_if": False},
            {"id": "documentary_evidence", "label": "Can you produce documentary evidence (press, citations, awards) for each criterion?",
             "type": "boolean", "weight": 20},
        ],
        "alternatives_on_disqualify": ["EB-2-NIW", "O-1"],
    },
    "EB-2-NIW": {
        "name": "EB-2 National Interest Waiver",
        "description": "Green card for advanced-degree professionals whose work is in the national interest. Self-petition.",
        "country": "US",
        "questions": [
            {"id": "advanced_degree", "label": "Do you hold a master's degree or higher (or equivalent experience)?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "endeavor_substantial", "label": "Is your proposed endeavor of substantial merit and national importance?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "well_positioned", "label": "Can you demonstrate you are well-positioned to advance the endeavor (qualifications, plan, progress)?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "balance_of_factors", "label": "Would waiving the labor certification benefit the U.S. on balance?",
             "type": "boolean", "weight": 25},
        ],
        "alternatives_on_disqualify": ["EB-2", "EB-1A", "O-1"],
    },
    "L-1": {
        "name": "L-1 Intracompany Transferee",
        "description": "Transfer from a foreign affiliate to a U.S. office of the same company.",
        "country": "US",
        "questions": [
            {"id": "abroad_one_year", "label": "Have you worked at the foreign company for at least 1 year in the past 3?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "qualifying_relationship", "label": "Are the U.S. and foreign companies related (parent/subsidiary/branch/affiliate)?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
            {"id": "executive_or_specialized", "label": "Is your role executive/managerial (L-1A) or specialized knowledge (L-1B)?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
        ],
        "alternatives_on_disqualify": ["H-1B", "E-2"],
    },
    "TN": {
        "name": "TN Visa (NAFTA / USMCA)",
        "description": "For Canadian and Mexican professionals in specific occupations under USMCA.",
        "country": "US",
        "questions": [
            {"id": "is_ca_or_mx", "label": "Are you a citizen of Canada or Mexico?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "tn_occupation", "label": "Is your offered job on the USMCA professional occupations list?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "has_credentials", "label": "Do you have the required credentials (typically a bachelor's in the field)?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
        ],
        "alternatives_on_disqualify": ["H-1B"],
    },
    "F-1": {
        "name": "F-1 Student Visa",
        "description": "For full-time students at SEVP-certified institutions.",
        "country": "US",
        "questions": [
            {"id": "admitted_sevp", "label": "Have you been admitted to a SEVP-certified institution?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "financial_capacity", "label": "Can you demonstrate funds for first year of tuition + living expenses?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
            {"id": "ties_home_country", "label": "Can you demonstrate ties to your home country (intent to return)?",
             "type": "boolean", "weight": 20, "disqualifier_if": False},
            {"id": "english_proficiency", "label": "Do you have the English proficiency required by your program?",
             "type": "boolean", "weight": 15},
        ],
        "alternatives_on_disqualify": ["J-1"],
    },
    "I-130": {
        "name": "I-130 Family-Based Petition",
        "description": "Petition by a U.S. citizen or LPR for a qualifying relative.",
        "country": "US",
        "questions": [
            {"id": "petitioner_status", "label": "Is the petitioning relative a U.S. citizen or lawful permanent resident?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "qualifying_relationship", "label": "Is the relationship spouse / parent / child / sibling?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "bona_fide_relationship", "label": "Can you document a bona fide relationship?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
        ],
        "alternatives_on_disqualify": [],
    },
    "UK-Skilled-Worker": {
        "name": "UK Skilled Worker Visa",
        "description": "UK visa for skilled workers with a sponsoring licensed employer.",
        "country": "UK",
        "questions": [
            {"id": "has_cos", "label": "Do you have a Certificate of Sponsorship from a UK-licensed sponsor?",
             "type": "boolean", "weight": 35, "disqualifier_if": False},
            {"id": "salary_threshold", "label": "Does the offered salary meet the UK threshold (currently around £38,700 unless on shortage list)?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
            {"id": "english_b1", "label": "Do you meet the B1 English requirement?",
             "type": "boolean", "weight": 20, "disqualifier_if": False},
            {"id": "no_uk_refusal", "label": "No prior UK refusals?",
             "type": "boolean", "weight": 15},
        ],
        "alternatives_on_disqualify": ["UK-Student"],
    },
    "CA-Express-Entry": {
        "name": "Canada Express Entry",
        "description": "Federal Skilled Worker / Canadian Experience Class / Federal Skilled Trades.",
        "country": "CA",
        "questions": [
            {"id": "skilled_experience", "label": "Do you have at least 1 year of skilled work experience (TEER 0-3)?",
             "type": "boolean", "weight": 30, "disqualifier_if": False},
            {"id": "language_test", "label": "Do you have valid IELTS / CELPIP / TEF / TCF results?",
             "type": "boolean", "weight": 25, "disqualifier_if": False},
            {"id": "age_under_45", "label": "Are you under 45?",
             "type": "boolean", "weight": 20},
            {"id": "education_recognized", "label": "Do you have a recognized post-secondary credential (with ECA if foreign)?",
             "type": "boolean", "weight": 15},
            {"id": "settlement_funds", "label": "Do you have the required settlement funds (if applying under FSW)?",
             "type": "boolean", "weight": 10},
        ],
        "alternatives_on_disqualify": ["CA-Study-Permit"],
    },
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class EligibilityCheckerService:
    """Public-facing visa eligibility checker."""

    def __init__(self) -> None:
        self._answers: dict[str, dict] = {}     # answer_id → record

    @staticmethod
    def list_pathways(country: str | None = None) -> list[dict]:
        out = []
        for pid, p in PATHWAYS.items():
            if country and p["country"] != country.upper():
                continue
            out.append({
                "id": pid, "name": p["name"], "description": p["description"],
                "country": p["country"], "question_count": len(p["questions"]),
            })
        return out

    @staticmethod
    def get_pathway(pathway_id: str) -> dict | None:
        p = PATHWAYS.get(pathway_id)
        if p is None:
            return None
        return {**p, "id": pathway_id}

    def evaluate(
        self,
        pathway_id: str,
        answers: dict[str, Any],
        applicant_email: str | None = None,
    ) -> dict:
        pathway = PATHWAYS.get(pathway_id)
        if pathway is None:
            raise ValueError(f"Unknown pathway: {pathway_id}")

        # Score each question
        disqualifiers: list[dict] = []
        score = 0
        max_score = 0
        question_results: list[dict] = []
        for q in pathway["questions"]:
            qid = q["id"]
            answer_value = answers.get(qid)
            max_score += q["weight"]
            disq_value = q.get("disqualifier_if")
            disq_explicit_no = q.get("disqualifier_if_explicit_no", False)
            is_disq = False
            if disq_value is not None and answer_value == disq_value:
                is_disq = True
                disqualifiers.append({
                    "question": q["label"],
                    "your_answer": answer_value,
                })
            if disq_explicit_no and answer_value is False:
                is_disq = True
                disqualifiers.append({
                    "question": q["label"],
                    "your_answer": answer_value,
                })
            # Score (binary True = full weight; select with options = proportional)
            if answer_value is True:
                score += q["weight"]
            elif q["type"] == "select" and answer_value in (q.get("options") or []):
                opts = q["options"]
                idx = opts.index(answer_value)
                score += int(q["weight"] * (idx / max(1, len(opts) - 1)))
            question_results.append({
                "id": qid, "label": q["label"],
                "your_answer": answer_value,
                "weight": q["weight"], "is_disqualifier": is_disq,
            })

        confidence_pct = round((score / max_score) * 100, 1) if max_score else 0
        eligible = len(disqualifiers) == 0 and confidence_pct >= 50
        likely_qualified = len(disqualifiers) == 0 and confidence_pct >= 70

        # Recommended next step
        if likely_qualified:
            recommendation = (
                f"You appear qualified for the {pathway['name']}. "
                "We recommend completing the full intake to get matched with a verified attorney."
            )
            next_step = "full_intake"
        elif eligible:
            recommendation = (
                f"You may qualify for the {pathway['name']} but borderline. "
                "Talk to a verified attorney to assess your specific situation."
            )
            next_step = "consultation"
        elif disqualifiers:
            recommendation = (
                f"Based on your answers, you don't currently qualify for the {pathway['name']}. "
                "There may be alternative pathways."
            )
            next_step = "explore_alternatives"
        else:
            recommendation = (
                "You may qualify but we'd need more information. "
                "A consultation with a verified attorney is the right next step."
            )
            next_step = "consultation"

        result = {
            "id": str(uuid.uuid4()),
            "pathway_id": pathway_id, "pathway_name": pathway["name"],
            "country": pathway["country"],
            "confidence_pct": confidence_pct,
            "eligible": eligible,
            "likely_qualified": likely_qualified,
            "disqualifiers": disqualifiers,
            "question_results": question_results,
            "recommendation": recommendation,
            "next_step": next_step,
            "alternatives": pathway.get("alternatives_on_disqualify", []),
            "shareable_hash": _hash_answers(pathway_id, answers),
            "applicant_email": applicant_email,
            "evaluated_at": datetime.utcnow().isoformat(),
            "disclosure": (
                "This is an automated eligibility check based on your answers. "
                "It is not legal advice and does not guarantee approval. "
                "Each case is decided on its individual merits."
            ),
        }
        self._answers[result["id"]] = result
        return result

    def evaluate_all_for_country(self, country: str, answers: dict[str, Any]) -> dict:
        """Run the same answers against every pathway in a country and return
        a ranked list. Useful for the "What visa fits me?" funnel."""
        country = country.upper()
        results = []
        for pid, p in PATHWAYS.items():
            if p["country"] != country:
                continue
            try:
                # Only evaluate pathways where the applicant answered at least
                # one of the relevant questions
                relevant_qids = {q["id"] for q in p["questions"]}
                if not (relevant_qids & set(answers.keys())):
                    continue
                r = self.evaluate(pid, answers)
                results.append(r)
            except ValueError:
                continue
        # Rank by confidence; eligible cases first
        results.sort(key=lambda r: (-int(r["likely_qualified"]), -int(r["eligible"]), -r["confidence_pct"]))
        return {
            "id": str(uuid.uuid4()),
            "country": country,
            "evaluated_count": len(results),
            "results": results,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    def get_evaluation(self, evaluation_id: str) -> dict | None:
        return self._answers.get(evaluation_id)


def _hash_answers(pathway_id: str, answers: dict) -> str:
    payload = json.dumps({"p": pathway_id, "a": answers}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:12]
