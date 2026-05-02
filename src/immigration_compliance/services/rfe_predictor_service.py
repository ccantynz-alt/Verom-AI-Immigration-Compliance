"""RFE (Request for Evidence) Risk Predictor — pre-filing risk assessment.

USCIS issues RFEs at high rates for predictable reasons. This service analyzes a case
profile against documented RFE patterns and produces:
  - overall RFE risk score (0-100)
  - specific predicted triggers with citations
  - mitigation recommendations
  - estimated risk reduction if recommendations are applied

The trigger library is hand-curated from USCIS Policy Manual, AAO decisions, and
practitioner experience. Each trigger has a pattern, severity, and mitigation."""

from __future__ import annotations

from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# RFE Trigger Library
# ---------------------------------------------------------------------------

RFE_TRIGGERS: dict[str, list[dict[str, Any]]] = {
    "H-1B": [
        {
            "code": "SPECIALTY_OCCUPATION_LEVEL_I",
            "pattern": {"wage_level": "I"},
            "severity": "high",
            "title": "Wage Level I + specialty occupation challenge",
            "explanation": (
                "USCIS frequently issues RFEs questioning specialty-occupation status when "
                "the position is paid at Wage Level I (entry-level). The argument: a specialty "
                "occupation requires professional-level skills that wouldn't be entry-level."
            ),
            "citation": "USCIS PM Vol. 2 Part F; AAO non-precedent decisions on Level I positions",
            "base_probability": 0.55,
            "mitigation": [
                "Provide detailed job description showing duties require specialized knowledge",
                "Cite OOH/O*NET entries showing the position requires bachelor's degree minimum",
                "Provide expert opinion letter from independent industry expert",
                "Document employer's organizational structure and the role's complexity",
            ],
        },
        {
            "code": "DEGREE_FIELD_MISMATCH",
            "pattern": {"degree_field_matches_role": False},
            "severity": "high",
            "title": "Degree field doesn't directly match the role",
            "explanation": (
                "When the beneficiary's degree is not in a field directly related to the offered "
                "position, USCIS issues RFEs requesting evidence of the connection."
            ),
            "citation": "USCIS PM specialty occupation guidance",
            "base_probability": 0.65,
            "mitigation": [
                "Provide expert evaluation showing equivalency between degree and role",
                "Document coursework that supports the role's required knowledge",
                "Provide industry letters showing the role accepts the degree field",
            ],
        },
        {
            "code": "EMPLOYER_EMPLOYEE_RELATIONSHIP",
            "pattern": {"third_party_placement": True},
            "severity": "high",
            "title": "Employer-employee relationship at third-party site",
            "explanation": (
                "For H-1B placements at third-party worksites, USCIS scrutinizes whether the "
                "petitioner has the right to control the beneficiary's work."
            ),
            "citation": "Defensor v. Meissner; USCIS Memo Itinerary requirements",
            "base_probability": 0.70,
            "mitigation": [
                "Provide complete itinerary covering full requested period",
                "Provide end-client letter confirming work assignment and duration",
                "Provide MSA/SOW between petitioner and end client",
                "Document petitioner's right to hire, fire, supervise, and pay the beneficiary",
            ],
        },
        {
            "code": "MAINTENANCE_OF_STATUS",
            "pattern": {"current_status_in_us": "F-1_OPT", "extension_request": True},
            "severity": "medium",
            "title": "Maintenance of status questions",
            "explanation": (
                "When transitioning from F-1 OPT to H-1B, gaps or unauthorized employment "
                "can trigger RFEs questioning maintenance of status."
            ),
            "citation": "8 CFR 214.2(h)",
            "base_probability": 0.20,
            "mitigation": [
                "Document continuous OPT employment authorization",
                "Verify cap-gap eligibility was properly invoked",
                "Provide pay stubs and employment letters covering the OPT period",
            ],
        },
    ],
    "O-1": [
        {
            "code": "INSUFFICIENT_CRITERIA_EVIDENCE",
            "pattern": {"criteria_count_lt": 4},
            "severity": "high",
            "title": "Marginal evidence on 3 of 8 criteria",
            "explanation": (
                "USCIS applies a two-step Kazarian analysis: first count criteria met, then "
                "evaluate the totality. Marginal evidence on the minimum 3 criteria triggers RFEs "
                "questioning whether 'extraordinary ability' is truly demonstrated."
            ),
            "citation": "Kazarian v. USCIS; USCIS PM Vol. 2 Part M Chapter 4",
            "base_probability": 0.60,
            "mitigation": [
                "Build evidence on a 4th and 5th criterion",
                "Strengthen each criterion with both quantity and quality of evidence",
                "Obtain expert letters that specifically address each criterion",
            ],
        },
        {
            "code": "WEAK_EXPERT_LETTERS",
            "pattern": {"expert_letters_quality": "generic"},
            "severity": "high",
            "title": "Generic or non-independent expert letters",
            "explanation": (
                "USCIS heavily discounts expert letters that are generic, written by close "
                "collaborators, or that don't specifically explain why the beneficiary's work "
                "is original and significant."
            ),
            "citation": "AAO non-precedent decisions on expert letters",
            "base_probability": 0.55,
            "mitigation": [
                "Obtain letters from independent experts (not close collaborators)",
                "Each letter should: explain expert's qualifications, describe the beneficiary's "
                "specific contributions, and explain field-wide significance",
                "Avoid template-style letters",
            ],
        },
        {
            "code": "PRESS_COVERAGE_QUALITY",
            "pattern": {"press_coverage_quality": "trade_only"},
            "severity": "medium",
            "title": "Press coverage limited to trade publications",
            "explanation": (
                "Press coverage in trade-only publications can satisfy the criterion but often "
                "draws RFEs requesting evidence of the publication's significance."
            ),
            "citation": "8 CFR 204.5(h)(3)(iii)",
            "base_probability": 0.35,
            "mitigation": [
                "Document the publication's circulation, audience, and editorial standards",
                "Add coverage in major media if available",
                "Provide context about why trade coverage matters in the field",
            ],
        },
    ],
    "I-485": [
        {
            "code": "I864_DEFICIENCY",
            "pattern": {"i864_strong": False},
            "severity": "high",
            "title": "I-864 Affidavit of Support deficiency",
            "explanation": (
                "Insufficient income, missing tax returns, or missing employment evidence "
                "trigger RFEs on the I-864."
            ),
            "citation": "8 USC 1183a; USCIS PM Vol. 14",
            "base_probability": 0.50,
            "mitigation": [
                "Document sponsor income with most recent 3 years of tax returns",
                "Obtain joint sponsor if income is below 125% of poverty guidelines",
                "Include current employment letter and pay stubs (last 6 months)",
            ],
        },
        {
            "code": "MEDICAL_EXAM_OUTDATED",
            "pattern": {"medical_complete": False},
            "severity": "medium",
            "title": "I-693 medical exam missing or expired",
            "explanation": "I-693 must be properly sealed and current at time of adjudication.",
            "citation": "8 CFR 245.5",
            "base_probability": 0.30,
            "mitigation": [
                "Submit I-693 in sealed envelope from civil surgeon",
                "Verify medical was completed within 60 days of submission (best practice)",
                "Confirm all required vaccinations are documented",
            ],
        },
        {
            "code": "STATUS_VIOLATION",
            "pattern": {"lawful_status_maintained": False},
            "severity": "high",
            "title": "Maintenance of lawful status questions",
            "explanation": (
                "Any gap in lawful status, unauthorized employment, or status violation triggers "
                "RFEs questioning eligibility under 245(a) or 245(c)."
            ),
            "citation": "INA 245(a), 245(c), 245(k)",
            "base_probability": 0.65,
            "mitigation": [
                "Analyze 245(k) eligibility (employment-based: <180 days violation)",
                "Document any time spent out of status in detail",
                "Consider consular processing if 245 ineligible",
            ],
        },
    ],
    "F-1": [
        {
            "code": "FINANCIAL_INSUFFICIENCY",
            "pattern": {"financial_sufficient": False},
            "severity": "blocking",
            "title": "Insufficient financial documentation",
            "explanation": (
                "Consular officers and USCIS routinely deny or RFE F-1 applications where the "
                "applicant cannot show full first-year funding."
            ),
            "citation": "9 FAM 402.5; 8 CFR 214.2(f)",
            "base_probability": 0.80,
            "mitigation": [
                "Document funds covering tuition + living expenses for the full first year",
                "Provide bank statements (last 3-6 months) and sponsor affidavits",
                "Document subsequent-year funding plan if I-20 covers multi-year program",
            ],
        },
        {
            "code": "WEAK_TIES_TO_HOME",
            "pattern": {"intent_to_return": False},
            "severity": "high",
            "title": "Weak ties to home country (214(b) concern)",
            "explanation": (
                "F-1 applicants must overcome the presumption of immigrant intent under "
                "INA 214(b). Weak ties drive most consular F-1 denials."
            ),
            "citation": "INA 214(b)",
            "base_probability": 0.55,
            "mitigation": [
                "Document family ties, property ownership, employment offers post-graduation",
                "Prepare clear study plan showing how the degree benefits the home country",
                "Practice the interview with focus on return intent",
            ],
        },
    ],
    "I-130": [
        {
            "code": "MARRIAGE_FRAUD_INDICATORS",
            "pattern": {"prior_petitions": True, "relationship": "spouse"},
            "severity": "high",
            "title": "Multiple I-130 spouse petitions — fraud indicators",
            "explanation": (
                "INA 204(c) bars approval if a prior marriage was found to be fraudulent. "
                "Multiple prior petitions trigger heightened scrutiny."
            ),
            "citation": "INA 204(c); Matter of Tawfik",
            "base_probability": 0.70,
            "mitigation": [
                "Document the bona fide nature of the current relationship comprehensively",
                "Include joint financial accounts, leases, photos, affidavits from third parties",
                "Address the prior marriage(s) directly with explanatory affidavit",
            ],
        },
        {
            "code": "INSUFFICIENT_RELATIONSHIP_EVIDENCE",
            "pattern": {"comprehensive_relationship_evidence": False},
            "severity": "medium",
            "title": "Insufficient relationship evidence",
            "explanation": "Sparse documentation of joint life triggers RFEs on bona fides.",
            "citation": "8 CFR 204.2(a)",
            "base_probability": 0.50,
            "mitigation": [
                "Provide joint accounts, joint lease/mortgage, joint tax returns",
                "Include photos across multiple years and locations",
                "Provide affidavits from family/friends with personal knowledge",
            ],
        },
    ],
}


class RFEPredictorService:
    """Predict RFE risk for a case before filing."""

    def predict(self, visa_type: str, case_profile: dict) -> dict:
        """Predict RFE risk and identify specific likely triggers."""
        triggers = RFE_TRIGGERS.get(visa_type, [])
        fired_triggers = []
        max_severity_weight = {"blocking": 1.0, "high": 0.7, "medium": 0.4, "low": 0.2}

        # Compute fired triggers
        for trigger in triggers:
            if self._matches(trigger["pattern"], case_profile):
                fired_triggers.append(trigger)

        # Aggregate probability — combined complement of independent risks
        risk_score = 0.0
        if fired_triggers:
            # Use 1 - product(1 - p_i) but cap at 0.95 to avoid implying certainty
            inverse = 1.0
            for t in fired_triggers:
                inverse *= (1.0 - t["base_probability"])
            risk_score = min(0.95, 1.0 - inverse)

        # Risk tier
        tier = (
            "very_high" if risk_score >= 0.7 else
            "high" if risk_score >= 0.5 else
            "moderate" if risk_score >= 0.3 else
            "low"
        )

        # Total mitigation steps
        mitigation_steps = []
        for t in fired_triggers:
            for m in t["mitigation"]:
                mitigation_steps.append({"trigger_code": t["code"], "step": m})

        # Estimate post-mitigation risk (assume 60% trigger probability reduction with full mitigation)
        post_mitigation_inverse = 1.0
        for t in fired_triggers:
            reduced_p = t["base_probability"] * 0.4
            post_mitigation_inverse *= (1.0 - reduced_p)
        post_mitigation_risk = round((1.0 - post_mitigation_inverse) * 100) if fired_triggers else 0

        return {
            "visa_type": visa_type,
            "risk_score": round(risk_score * 100),
            "risk_tier": tier,
            "total_triggers": len(fired_triggers),
            "fired_triggers": [
                {
                    "code": t["code"],
                    "title": t["title"],
                    "severity": t["severity"],
                    "explanation": t["explanation"],
                    "citation": t["citation"],
                    "base_probability_pct": int(t["base_probability"] * 100),
                    "mitigation": t["mitigation"],
                }
                for t in fired_triggers
            ],
            "mitigation_steps": mitigation_steps,
            "post_mitigation_risk_pct": post_mitigation_risk,
            "risk_reduction_pct": round(risk_score * 100) - post_mitigation_risk,
            "predicted_at": datetime.utcnow().isoformat(),
            "disclaimer": (
                "Predictions are based on historical RFE patterns and are advisory only. "
                "Each case is evaluated on its own merits by USCIS."
            ),
        }

    @staticmethod
    def _matches(pattern: dict, case_profile: dict) -> bool:
        """Check whether case_profile matches the trigger pattern."""
        for key, expected in pattern.items():
            if key.endswith("_lt"):
                base = key[:-3]
                actual = case_profile.get(base)
                try:
                    if actual is None or float(actual) >= float(expected):
                        return False
                except (TypeError, ValueError):
                    return False
            elif key.endswith("_gt"):
                base = key[:-3]
                actual = case_profile.get(base)
                try:
                    if actual is None or float(actual) <= float(expected):
                        return False
                except (TypeError, ValueError):
                    return False
            else:
                if case_profile.get(key) != expected:
                    return False
        return True

    def list_known_triggers(self, visa_type: str) -> list[dict]:
        """Documentation endpoint — list all triggers we know for a visa type."""
        triggers = RFE_TRIGGERS.get(visa_type, [])
        return [
            {
                "code": t["code"],
                "title": t["title"],
                "severity": t["severity"],
                "citation": t["citation"],
                "base_probability_pct": int(t["base_probability"] * 100),
            }
            for t in triggers
        ]

    def get_industry_baselines(self) -> dict:
        """Aggregate RFE statistics by visa type — used for benchmarking."""
        # Reference points from USCIS data releases (rounded, advisory)
        return {
            "H-1B": {"industry_rfe_rate_pct": 22, "trend": "stable", "source": "USCIS data 2023-2024"},
            "O-1": {"industry_rfe_rate_pct": 35, "trend": "increasing", "source": "USCIS data 2023-2024"},
            "I-485": {"industry_rfe_rate_pct": 15, "trend": "stable", "source": "USCIS data 2023-2024"},
            "I-130": {"industry_rfe_rate_pct": 10, "trend": "stable", "source": "USCIS data 2023-2024"},
            "F-1": {"industry_rfe_rate_pct": 8, "trend": "stable", "source": "USCIS data + DOS consular trends"},
            "L-1": {"industry_rfe_rate_pct": 28, "trend": "stable", "source": "USCIS data 2023-2024"},
            "as_of": datetime.utcnow().isoformat(),
            "disclaimer": "Industry baselines are advisory and based on aggregate USCIS data.",
        }
