"""AI Intake Engine — adaptive questionnaires, document checklists, red-flag detection,
application strength scoring. Powers the magical onboarding for applicants and attorneys.

This is rules-based AI: deterministic, explainable, auditable. Every recommendation has
a reason chain, every red flag has a citation, every strength score has component math.

The engine is keyed on (visa_type, country) and falls back to family-level defaults
when a specific configuration is unknown."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Visa configuration registry
# ---------------------------------------------------------------------------

# Each visa type has: family, country, base_documents, key_questions, eligibility_rules,
# strength_factors, common_red_flags. New countries/visa types can be added by extending
# this registry — the rest of the engine is data-driven.
VISA_REGISTRY: dict[str, dict[str, Any]] = {
    # ---------------- United States ----------------
    "F-1": {
        "country": "US",
        "family": "student",
        "name": "F-1 Student Visa",
        "agency": "USCIS / DOS",
        "base_documents": [
            "valid_passport", "i20", "sevis_fee_receipt", "ds160_confirmation",
            "financial_evidence", "academic_transcripts", "standardized_test_scores",
            "school_admission_letter", "photo_ds_compliant",
        ],
        "key_questions": [
            {"id": "school_admitted", "type": "boolean", "label": "Have you been formally admitted to a SEVP-certified school?", "required": True, "blocking_if_false": True},
            {"id": "financial_sufficient", "type": "boolean", "label": "Can you demonstrate funds for first year of tuition + living expenses?", "required": True, "blocking_if_false": True},
            {"id": "intent_to_return", "type": "boolean", "label": "Do you intend to return to your home country after completing studies?", "required": True},
            {"id": "prior_us_visa_denial", "type": "boolean", "label": "Have you previously been denied a US visa?", "required": True},
            {"id": "prior_immigration_violation", "type": "boolean", "label": "Have you ever overstayed a US visa or violated US immigration law?", "required": True},
            {"id": "english_proficiency", "type": "select", "label": "English proficiency", "options": ["native", "advanced", "intermediate", "basic", "none"], "required": True},
        ],
        "eligibility_rules": [
            {"rule": "school_admitted == True", "message": "Must have I-20 from SEVP-certified institution"},
            {"rule": "financial_sufficient == True", "message": "Must demonstrate financial capacity for full first year"},
        ],
        "strength_factors": [
            {"id": "tier1_school", "weight": 15, "description": "Top-tier accredited institution"},
            {"id": "scholarship_funded", "weight": 15, "description": "Merit scholarship or assistantship"},
            {"id": "strong_academic_record", "weight": 15, "description": "Strong undergraduate GPA / standardized tests"},
            {"id": "clear_career_plan", "weight": 10, "description": "Articulated career plan in home country"},
            {"id": "ties_to_home_country", "weight": 15, "description": "Demonstrable ties to home country"},
            {"id": "clean_immigration_history", "weight": 15, "description": "No prior denials or overstays"},
            {"id": "english_fluency", "weight": 10, "description": "Strong English proficiency"},
            {"id": "complete_documentation", "weight": 5, "description": "All required documents prepared"},
        ],
    },
    "H-1B": {
        "country": "US",
        "family": "work",
        "name": "H-1B Specialty Occupation",
        "agency": "USCIS",
        "base_documents": [
            "valid_passport", "bachelors_degree_or_equivalent", "academic_transcripts",
            "resume_cv", "employment_offer_letter", "lca_certified",
            "employer_supporting_documents", "specialty_occupation_evidence",
            "employer_employee_relationship_evidence",
        ],
        "key_questions": [
            {"id": "has_bachelors_or_higher", "type": "boolean", "label": "Do you hold a US bachelor's degree (or foreign equivalent) in a field related to the offered position?", "required": True, "blocking_if_false": True},
            {"id": "has_us_employer_offer", "type": "boolean", "label": "Do you have a written job offer from a US employer?", "required": True, "blocking_if_false": True},
            {"id": "lca_filed", "type": "boolean", "label": "Has the employer filed a certified Labor Condition Application (LCA)?", "required": True},
            {"id": "wage_level", "type": "select", "label": "What wage level is the offered salary?", "options": ["I", "II", "III", "IV"], "required": True},
            {"id": "us_masters_or_higher", "type": "boolean", "label": "Do you hold a US master's degree or higher?", "required": False},
            {"id": "selected_in_lottery", "type": "boolean", "label": "Have you been selected in the H-1B registration lottery?", "required": True},
            {"id": "prior_h1b_approval", "type": "boolean", "label": "Have you previously held H-1B status?", "required": True},
            {"id": "current_status_in_us", "type": "select", "label": "Current immigration status in US", "options": ["F-1_OPT", "F-1_STEM_OPT", "L-1", "H-4", "TN", "outside_US", "other"], "required": True},
        ],
        "eligibility_rules": [
            {"rule": "has_bachelors_or_higher == True", "message": "H-1B requires bachelor's degree or equivalent in specialty field"},
            {"rule": "has_us_employer_offer == True", "message": "Must have US employer sponsorship"},
            {"rule": "lca_filed == True", "message": "LCA must be certified before H-1B petition"},
        ],
        "strength_factors": [
            {"id": "us_masters_or_higher", "weight": 15, "description": "US master's degree (lottery advantage + specialty fit)"},
            {"id": "specialty_occupation_clear", "weight": 20, "description": "Position clearly meets specialty occupation criteria"},
            {"id": "wage_level_iii_or_iv", "weight": 15, "description": "Wage level III or IV (strengthens specialty argument)"},
            {"id": "employer_track_record", "weight": 10, "description": "Employer has prior H-1B approvals"},
            {"id": "lca_certified", "weight": 10, "description": "LCA certified for the role"},
            {"id": "selected_in_lottery", "weight": 15, "description": "Selected in registration lottery"},
            {"id": "no_prior_denials", "weight": 10, "description": "No prior H-1B denials"},
            {"id": "strong_field_match", "weight": 5, "description": "Degree field matches occupation"},
        ],
    },
    "O-1": {
        "country": "US",
        "family": "work",
        "name": "O-1 Extraordinary Ability",
        "agency": "USCIS",
        "base_documents": [
            "valid_passport", "resume_cv", "employment_offer_or_itinerary",
            "advisory_opinion_or_peer_consultation", "expert_letters",
            "evidence_of_awards", "evidence_of_publications", "evidence_of_judging",
            "evidence_of_press_coverage", "evidence_of_high_salary",
            "evidence_of_membership", "evidence_of_original_contributions",
        ],
        "key_questions": [
            {"id": "criteria_awards", "type": "boolean", "label": "Have you received nationally or internationally recognized awards?"},
            {"id": "criteria_membership", "type": "boolean", "label": "Are you a member of associations requiring outstanding achievement?"},
            {"id": "criteria_press", "type": "boolean", "label": "Has there been published material about you in major media?"},
            {"id": "criteria_judging", "type": "boolean", "label": "Have you served as a judge of others' work in your field?"},
            {"id": "criteria_original_contribution", "type": "boolean", "label": "Have you made original scientific/scholarly/business contributions of major significance?"},
            {"id": "criteria_publications", "type": "boolean", "label": "Have you authored scholarly articles in major media or trade publications?"},
            {"id": "criteria_critical_role", "type": "boolean", "label": "Have you played critical/essential roles for distinguished organizations?"},
            {"id": "criteria_high_salary", "type": "boolean", "label": "Do you command a high salary relative to others in your field?"},
            {"id": "has_advisory_opinion", "type": "boolean", "label": "Have you obtained an advisory opinion from a peer group / labor org?"},
        ],
        "eligibility_rules": [
            {"rule": "min_criteria_count(3)", "message": "Must satisfy at least 3 of 8 evidentiary criteria"},
        ],
        "strength_factors": [
            {"id": "criteria_count_5_plus", "weight": 25, "description": "5+ evidentiary criteria satisfied"},
            {"id": "criteria_count_4", "weight": 18, "description": "4 evidentiary criteria satisfied"},
            {"id": "criteria_count_3", "weight": 10, "description": "3 evidentiary criteria satisfied (minimum)"},
            {"id": "international_recognition", "weight": 15, "description": "International recognition demonstrated"},
            {"id": "expert_letters_strong", "weight": 15, "description": "Strong, specific expert letters from independent experts"},
            {"id": "advisory_opinion", "weight": 10, "description": "Favorable advisory opinion obtained"},
            {"id": "press_coverage_major", "weight": 10, "description": "Press coverage in major outlets"},
            {"id": "high_salary_documented", "weight": 5, "description": "High salary clearly documented vs. peers"},
            {"id": "no_prior_denials", "weight": 10, "description": "No prior O-1 denials"},
            {"id": "us_employer_petitioner", "weight": 5, "description": "US employer/agent as petitioner"},
        ],
    },
    "I-130": {
        "country": "US",
        "family": "family",
        "name": "I-130 Petition for Alien Relative",
        "agency": "USCIS",
        "base_documents": [
            "petitioner_us_citizenship_or_lpr_evidence", "marriage_certificate_if_applicable",
            "birth_certificates", "proof_of_relationship",
            "passport_photos", "petitioner_id", "beneficiary_id",
            "divorce_decrees_if_applicable", "financial_support_evidence",
        ],
        "key_questions": [
            {"id": "petitioner_status", "type": "select", "label": "Petitioner's status", "options": ["US_citizen", "lawful_permanent_resident"], "required": True, "blocking_if_false": True},
            {"id": "relationship", "type": "select", "label": "Relationship to beneficiary", "options": ["spouse", "parent", "child_under_21_unmarried", "child_over_21_unmarried", "child_married", "sibling"], "required": True},
            {"id": "marriage_bona_fide", "type": "boolean", "label": "If spouse: marriage is bona fide and not for immigration purposes"},
            {"id": "prior_petitions", "type": "boolean", "label": "Has petitioner filed prior I-130s for any spouse?"},
            {"id": "beneficiary_in_us", "type": "boolean", "label": "Is the beneficiary currently in the US?"},
            {"id": "beneficiary_inadmissible_grounds", "type": "boolean", "label": "Are there any potential inadmissibility issues (criminal, immigration, health)?"},
        ],
        "eligibility_rules": [
            {"rule": "petitioner_status in ['US_citizen', 'lawful_permanent_resident']", "message": "Petitioner must be USC or LPR"},
        ],
        "strength_factors": [
            {"id": "us_citizen_petitioner", "weight": 15, "description": "USC petitioner (immediate relative — no wait)"},
            {"id": "comprehensive_relationship_evidence", "weight": 25, "description": "Comprehensive joint relationship evidence"},
            {"id": "no_prior_petitions", "weight": 10, "description": "No prior I-130 marriage petitions"},
            {"id": "clean_inadmissibility", "weight": 20, "description": "No inadmissibility issues"},
            {"id": "financial_support_clear", "weight": 10, "description": "Affidavit of support documentation prepared"},
            {"id": "complete_documentation", "weight": 20, "description": "All required documents prepared"},
        ],
    },
    "I-485": {
        "country": "US",
        "family": "pr",
        "name": "I-485 Adjustment of Status",
        "agency": "USCIS",
        "base_documents": [
            "valid_passport", "i94_record", "approved_i130_or_i140",
            "birth_certificate", "marriage_certificate_if_applicable",
            "i693_medical_exam", "i864_affidavit_of_support",
            "passport_photos", "current_immigration_status_evidence",
            "tax_returns_3_years",
        ],
        "key_questions": [
            {"id": "underlying_petition_approved", "type": "boolean", "label": "Has the underlying petition (I-130 or I-140) been approved?", "required": True, "blocking_if_false": True},
            {"id": "priority_date_current", "type": "boolean", "label": "Is your priority date current per the latest Visa Bulletin?", "required": True, "blocking_if_false": True},
            {"id": "lawful_status_maintained", "type": "boolean", "label": "Have you maintained lawful immigration status since entry?", "required": True},
            {"id": "criminal_history", "type": "boolean", "label": "Do you have any criminal arrests or convictions?", "required": True},
            {"id": "previously_removed", "type": "boolean", "label": "Have you ever been removed/deported or in removal proceedings?", "required": True},
            {"id": "public_charge_concern", "type": "boolean", "label": "Have you used public benefits in the US?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "underlying_petition_approved == True", "message": "I-130 or I-140 must be approved"},
            {"rule": "priority_date_current == True", "message": "Priority date must be current to file"},
        ],
        "strength_factors": [
            {"id": "priority_date_current", "weight": 20, "description": "Priority date current"},
            {"id": "clean_criminal", "weight": 20, "description": "No criminal history"},
            {"id": "lawful_status_maintained", "weight": 15, "description": "Status maintained continuously"},
            {"id": "no_public_charge", "weight": 10, "description": "No public charge concerns"},
            {"id": "i864_strong", "weight": 15, "description": "Strong I-864 / financial sponsor"},
            {"id": "medical_complete", "weight": 10, "description": "I-693 medical complete and current"},
            {"id": "complete_documentation", "weight": 10, "description": "Full documentation prepared"},
        ],
    },
    # ---------------- United Kingdom ----------------
    "UK-Student": {
        "country": "UK",
        "family": "student",
        "name": "UK Student Visa",
        "agency": "UKVI / Home Office",
        "base_documents": [
            "valid_passport", "cas_letter", "financial_evidence_28_days",
            "tb_test_if_required", "english_proficiency_certificate",
            "academic_qualifications", "atas_certificate_if_required",
            "parental_consent_if_under_18",
        ],
        "key_questions": [
            {"id": "has_cas", "type": "boolean", "label": "Do you have a Confirmation of Acceptance for Studies (CAS) from a licensed sponsor?", "required": True, "blocking_if_false": True},
            {"id": "financial_28_days", "type": "boolean", "label": "Can you show required funds held for at least 28 consecutive days?", "required": True, "blocking_if_false": True},
            {"id": "english_b2", "type": "boolean", "label": "Do you meet B2 English requirement (degree-level course)?", "required": True},
            {"id": "atas_required", "type": "boolean", "label": "Is your course ATAS-required?"},
            {"id": "prior_uk_refusal", "type": "boolean", "label": "Have you been refused a UK visa before?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "has_cas == True", "message": "Must have valid CAS from licensed sponsor"},
            {"rule": "financial_28_days == True", "message": "Must show maintenance funds for 28 consecutive days"},
        ],
        "strength_factors": [
            {"id": "russell_group_uni", "weight": 15, "description": "Russell Group / top-ranked institution"},
            {"id": "scholarship", "weight": 15, "description": "Scholarship or sponsored funding"},
            {"id": "strong_english", "weight": 15, "description": "Strong English proficiency above minimum"},
            {"id": "ties_to_home", "weight": 20, "description": "Strong ties to home country"},
            {"id": "no_prior_refusals", "weight": 15, "description": "No prior UK visa refusals"},
            {"id": "complete_documentation", "weight": 20, "description": "All required documents prepared"},
        ],
    },
    "UK-Skilled-Worker": {
        "country": "UK",
        "family": "work",
        "name": "UK Skilled Worker Visa",
        "agency": "UKVI / Home Office",
        "base_documents": [
            "valid_passport", "certificate_of_sponsorship", "english_proficiency_certificate",
            "salary_evidence", "academic_qualifications", "tb_test_if_required",
            "criminal_record_certificate_if_required",
        ],
        "key_questions": [
            {"id": "has_cos", "type": "boolean", "label": "Do you have a valid Certificate of Sponsorship from a licensed sponsor?", "required": True, "blocking_if_false": True},
            {"id": "salary_meets_threshold", "type": "boolean", "label": "Does the offered salary meet the going rate AND general threshold (currently £38,700 unless on shortage occupation list)?", "required": True, "blocking_if_false": True},
            {"id": "english_b1", "type": "boolean", "label": "Do you meet B1 English requirement?", "required": True},
            {"id": "shortage_occupation", "type": "boolean", "label": "Is the role on the Immigration Salary List?"},
            {"id": "prior_uk_refusal", "type": "boolean", "label": "Have you been refused a UK visa before?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "has_cos == True", "message": "Valid Certificate of Sponsorship required"},
            {"rule": "salary_meets_threshold == True", "message": "Salary must meet UKVI threshold for the role"},
        ],
        "strength_factors": [
            {"id": "salary_above_threshold", "weight": 20, "description": "Salary materially above threshold"},
            {"id": "shortage_occupation", "weight": 15, "description": "Role on Immigration Salary List"},
            {"id": "phd_relevant", "weight": 10, "description": "PhD relevant to the job"},
            {"id": "stem_phd", "weight": 5, "description": "PhD in STEM (additional points)"},
            {"id": "strong_english", "weight": 15, "description": "Strong English proficiency"},
            {"id": "no_prior_refusals", "weight": 15, "description": "No prior UK visa refusals"},
            {"id": "complete_documentation", "weight": 20, "description": "All required documents prepared"},
        ],
    },
    # ---------------- Canada ----------------
    "CA-Study-Permit": {
        "country": "CA",
        "family": "student",
        "name": "Canada Study Permit",
        "agency": "IRCC",
        "base_documents": [
            "valid_passport", "letter_of_acceptance_dli", "proof_of_funds_gic",
            "tuition_payment_proof", "study_plan_letter", "academic_transcripts",
            "language_test_results", "medical_exam_if_required",
            "police_certificate_if_required", "biometrics_confirmation",
        ],
        "key_questions": [
            {"id": "loa_dli", "type": "boolean", "label": "Have you been accepted to a Designated Learning Institution (DLI)?", "required": True, "blocking_if_false": True},
            {"id": "pal_pgwp_eligibility", "type": "boolean", "label": "Have you obtained a Provincial Attestation Letter (PAL) where required?", "required": True},
            {"id": "proof_of_funds", "type": "boolean", "label": "Can you demonstrate sufficient funds (CAD $20,635+ for cost of living, plus tuition)?", "required": True, "blocking_if_false": True},
            {"id": "intent_to_leave", "type": "boolean", "label": "Will you leave Canada when your studies end?", "required": True},
            {"id": "prior_refusal", "type": "boolean", "label": "Have you been refused a Canadian visa or permit before?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "loa_dli == True", "message": "LOA from DLI is mandatory"},
            {"rule": "proof_of_funds == True", "message": "Must meet IRCC financial requirements"},
        ],
        "strength_factors": [
            {"id": "tier1_dli", "weight": 15, "description": "Top-tier DLI (U15 / Polytechnics Canada)"},
            {"id": "scholarship", "weight": 15, "description": "Scholarship or funded program"},
            {"id": "gic_funded_full", "weight": 15, "description": "GIC funded above minimum"},
            {"id": "ties_to_home", "weight": 20, "description": "Strong ties to home country"},
            {"id": "no_prior_refusals", "weight": 15, "description": "No prior Canadian refusals"},
            {"id": "complete_documentation", "weight": 20, "description": "All required documents prepared"},
        ],
    },
    "CA-Express-Entry": {
        "country": "CA",
        "family": "pr",
        "name": "Canada Express Entry (FSW / CEC / FST)",
        "agency": "IRCC",
        "base_documents": [
            "valid_passport", "language_test_results", "ECA_credential_assessment",
            "work_experience_letters", "police_certificates_all_countries",
            "medical_exam", "proof_of_funds_if_FSW", "biometrics_confirmation",
        ],
        "key_questions": [
            {"id": "language_test_done", "type": "boolean", "label": "Do you have valid IELTS/CELPIP (English) or TEF/TCF (French) results?", "required": True, "blocking_if_false": True},
            {"id": "eca_done", "type": "boolean", "label": "Have you obtained an Educational Credential Assessment (ECA)?"},
            {"id": "noc_skill_level", "type": "select", "label": "NOC TEER level of your work experience", "options": ["TEER_0", "TEER_1", "TEER_2", "TEER_3", "TEER_4", "TEER_5"], "required": True},
            {"id": "years_experience", "type": "number", "label": "Years of skilled work experience", "required": True},
            {"id": "age", "type": "number", "label": "Age", "required": True},
            {"id": "canadian_experience", "type": "boolean", "label": "Do you have Canadian work or study experience?"},
            {"id": "spouse_french_speaker", "type": "boolean", "label": "Do you or your spouse speak French (CLB 7+)?"},
        ],
        "eligibility_rules": [
            {"rule": "language_test_done == True", "message": "Valid language test required"},
            {"rule": "noc_skill_level in ['TEER_0','TEER_1','TEER_2','TEER_3']", "message": "Skilled occupation (TEER 0-3) required for most streams"},
        ],
        "strength_factors": [
            {"id": "age_25_to_35", "weight": 15, "description": "Age 25-35 (max CRS points)"},
            {"id": "language_clb_9_plus", "weight": 20, "description": "CLB 9+ in language"},
            {"id": "canadian_experience", "weight": 15, "description": "Canadian work experience"},
            {"id": "masters_or_phd", "weight": 15, "description": "Master's or PhD"},
            {"id": "french_bonus", "weight": 10, "description": "French language proficiency"},
            {"id": "provincial_nomination", "weight": 15, "description": "Provincial nomination"},
            {"id": "skilled_experience_3_plus", "weight": 10, "description": "3+ years skilled work experience"},
        ],
    },
    # ---------------- Australia ----------------
    "AU-Subclass-500": {
        "country": "AU",
        "family": "student",
        "name": "Australia Subclass 500 Student Visa",
        "agency": "Department of Home Affairs",
        "base_documents": [
            "valid_passport", "coe_confirmation_of_enrolment", "gte_statement",
            "financial_capacity_evidence", "english_proficiency_test",
            "oshc_health_cover", "academic_transcripts", "biometrics_if_required",
        ],
        "key_questions": [
            {"id": "has_coe", "type": "boolean", "label": "Do you have a Confirmation of Enrolment (CoE)?", "required": True, "blocking_if_false": True},
            {"id": "gte_genuine", "type": "boolean", "label": "Can you demonstrate Genuine Temporary Entrant (GTE) intent?", "required": True},
            {"id": "financial_evidence", "type": "boolean", "label": "Can you demonstrate financial capacity (AUD ~$24,505/yr living costs + tuition)?", "required": True, "blocking_if_false": True},
            {"id": "oshc", "type": "boolean", "label": "Do you have Overseas Student Health Cover (OSHC)?", "required": True},
            {"id": "english_proficiency", "type": "boolean", "label": "Do you meet English requirements (IELTS 5.5+ typical)?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "has_coe == True", "message": "CoE from registered provider required"},
            {"rule": "financial_evidence == True", "message": "Must demonstrate financial capacity"},
        ],
        "strength_factors": [
            {"id": "go8_university", "weight": 15, "description": "Group of Eight university"},
            {"id": "strong_gte", "weight": 25, "description": "Strong GTE statement with clear study plan"},
            {"id": "scholarship", "weight": 15, "description": "Scholarship or sponsored program"},
            {"id": "strong_english", "weight": 15, "description": "Strong English above minimum"},
            {"id": "ties_to_home", "weight": 15, "description": "Strong ties to home country"},
            {"id": "complete_documentation", "weight": 15, "description": "All required documents prepared"},
        ],
    },
    "AU-Subclass-482": {
        "country": "AU",
        "family": "work",
        "name": "Australia Subclass 482 Skills in Demand",
        "agency": "Department of Home Affairs",
        "base_documents": [
            "valid_passport", "nomination_approval", "skills_assessment_if_required",
            "english_proficiency_test", "academic_qualifications",
            "work_experience_letters", "police_certificates", "health_examination",
        ],
        "key_questions": [
            {"id": "approved_sponsor", "type": "boolean", "label": "Is your employer an approved Australian sponsor?", "required": True, "blocking_if_false": True},
            {"id": "occupation_listed", "type": "boolean", "label": "Is the role on the Skills in Demand occupation list?", "required": True, "blocking_if_false": True},
            {"id": "salary_meets_tsmit", "type": "boolean", "label": "Does the salary meet TSMIT (currently AUD $73,150)?", "required": True},
            {"id": "english_competent", "type": "boolean", "label": "Do you meet English requirements (Competent English typical)?", "required": True},
            {"id": "two_years_experience", "type": "boolean", "label": "Do you have at least 2 years of relevant work experience?"},
        ],
        "eligibility_rules": [
            {"rule": "approved_sponsor == True", "message": "Employer must be approved sponsor"},
            {"rule": "occupation_listed == True", "message": "Occupation must be on relevant list"},
        ],
        "strength_factors": [
            {"id": "salary_well_above_tsmit", "weight": 15, "description": "Salary materially above TSMIT"},
            {"id": "occupation_specialist_skills", "weight": 15, "description": "On Specialist Skills pathway"},
            {"id": "5_plus_years_experience", "weight": 15, "description": "5+ years experience"},
            {"id": "skills_assessment_complete", "weight": 15, "description": "Skills assessment completed"},
            {"id": "strong_english", "weight": 15, "description": "Strong English proficiency"},
            {"id": "complete_documentation", "weight": 25, "description": "All required documents prepared"},
        ],
    },
    # ---------------- Germany ----------------
    "DE-Student": {
        "country": "DE",
        "family": "student",
        "name": "Germany Student Visa",
        "agency": "German Federal Foreign Office",
        "base_documents": [
            "valid_passport", "university_admission_letter", "blocked_account_evidence",
            "academic_transcripts", "language_proficiency_certificate",
            "health_insurance", "motivation_letter", "biometric_photos",
        ],
        "key_questions": [
            {"id": "uni_admission", "type": "boolean", "label": "Have you been admitted to a recognized German university?", "required": True, "blocking_if_false": True},
            {"id": "blocked_account", "type": "boolean", "label": "Have you set up a blocked account (€11,904+)?", "required": True, "blocking_if_false": True},
            {"id": "language_certified", "type": "boolean", "label": "Do you have proof of language proficiency (German B1+ or English for English-taught programs)?", "required": True},
            {"id": "health_insurance", "type": "boolean", "label": "Do you have valid German health insurance?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "uni_admission == True", "message": "University admission required"},
            {"rule": "blocked_account == True", "message": "Blocked account is mandatory"},
        ],
        "strength_factors": [
            {"id": "tu9_university", "weight": 15, "description": "TU9 / top-ranked German university"},
            {"id": "scholarship_daad", "weight": 15, "description": "DAAD or other scholarship"},
            {"id": "german_b2_plus", "weight": 15, "description": "German B2+ proficiency"},
            {"id": "ties_to_home", "weight": 20, "description": "Ties to home country"},
            {"id": "complete_documentation", "weight": 35, "description": "All required documents prepared"},
        ],
    },
    "DE-Blue-Card": {
        "country": "DE",
        "family": "work",
        "name": "Germany EU Blue Card",
        "agency": "Foreigners' Authority / Embassy",
        "base_documents": [
            "valid_passport", "employment_contract", "academic_qualifications",
            "anabin_university_evaluation", "salary_evidence",
            "german_health_insurance", "biometric_photos",
        ],
        "key_questions": [
            {"id": "german_employment_contract", "type": "boolean", "label": "Do you have a German employment contract?", "required": True, "blocking_if_false": True},
            {"id": "salary_meets_threshold", "type": "boolean", "label": "Does the salary meet the EU Blue Card threshold (€45,300 standard, €41,041 shortage)?", "required": True, "blocking_if_false": True},
            {"id": "degree_recognized", "type": "boolean", "label": "Is your degree recognized (anabin H+) or comparable to German degree?", "required": True, "blocking_if_false": True},
            {"id": "shortage_occupation", "type": "boolean", "label": "Is the role in a shortage occupation (IT, STEM, medical, etc.)?"},
        ],
        "eligibility_rules": [
            {"rule": "german_employment_contract == True", "message": "German employment contract required"},
            {"rule": "salary_meets_threshold == True", "message": "Salary must meet Blue Card threshold"},
        ],
        "strength_factors": [
            {"id": "salary_well_above_threshold", "weight": 15, "description": "Salary materially above threshold"},
            {"id": "shortage_occupation", "weight": 15, "description": "Shortage occupation"},
            {"id": "german_proficiency", "weight": 10, "description": "German B1+ proficiency"},
            {"id": "complete_documentation", "weight": 35, "description": "All required documents prepared"},
            {"id": "no_prior_refusals", "weight": 25, "description": "No prior visa refusals"},
        ],
    },
    # ---------------- New Zealand ----------------
    "NZ-Student": {
        "country": "NZ",
        "family": "student",
        "name": "New Zealand Student Visa",
        "agency": "Immigration New Zealand",
        "base_documents": [
            "valid_passport", "offer_of_place", "evidence_of_funds_NZD20K",
            "tuition_payment_proof", "english_proficiency_evidence",
            "medical_exam_if_required", "police_certificate_if_required",
            "acceptable_standard_of_health_certificate",
        ],
        "key_questions": [
            {"id": "has_offer_of_place", "type": "boolean", "label": "Do you have an Offer of Place from an INZ-approved education provider?", "required": True, "blocking_if_false": True},
            {"id": "funds_NZD15K_per_year", "type": "boolean", "label": "Can you show NZD $20,000+ per year for living costs (or NZD $1,667/month for short courses)?", "required": True, "blocking_if_false": True},
            {"id": "genuine_intent", "type": "boolean", "label": "Can you demonstrate genuine student intent and bona fide purpose?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "has_offer_of_place == True", "message": "Offer of Place required"},
            {"rule": "funds_NZD15K_per_year == True", "message": "Must show maintenance funds"},
        ],
        "strength_factors": [
            {"id": "tier1_provider", "weight": 20, "description": "Tier 1 NZ provider (universities, polytechnics)"},
            {"id": "scholarship", "weight": 15, "description": "Scholarship-funded"},
            {"id": "ties_to_home", "weight": 25, "description": "Strong ties to home country"},
            {"id": "complete_documentation", "weight": 40, "description": "All required documents prepared"},
        ],
    },
    "NZ-Skilled-Migrant": {
        "country": "NZ",
        "family": "pr",
        "name": "New Zealand Skilled Migrant Category",
        "agency": "Immigration New Zealand",
        "base_documents": [
            "valid_passport", "qualification_assessment_NZQA",
            "skilled_employment_offer", "english_proficiency_test",
            "police_certificates_all_countries", "medical_exam",
            "experience_letters",
        ],
        "key_questions": [
            {"id": "skilled_job_offer", "type": "boolean", "label": "Do you have a skilled job offer in NZ paying ≥ NZD $31.61/hr?", "required": True, "blocking_if_false": True},
            {"id": "qualification_recognized", "type": "boolean", "label": "Is your qualification recognized by NZQA?", "required": True},
            {"id": "english_test_done", "type": "boolean", "label": "Do you have IELTS 6.5+ or equivalent?", "required": True},
            {"id": "occupation_listed", "type": "boolean", "label": "Is your occupation on the Green List?"},
            {"id": "age_under_56", "type": "boolean", "label": "Are you under 56 years old?", "required": True},
        ],
        "eligibility_rules": [
            {"rule": "skilled_job_offer == True", "message": "Skilled job offer required"},
            {"rule": "age_under_56 == True", "message": "Must be under 56"},
        ],
        "strength_factors": [
            {"id": "green_list_tier1", "weight": 25, "description": "Green List Tier 1 occupation"},
            {"id": "salary_2x_threshold", "weight": 15, "description": "Salary 2x median"},
            {"id": "nz_experience", "weight": 15, "description": "NZ work experience"},
            {"id": "phd_or_masters_in_nz", "weight": 15, "description": "PhD or Master's earned in NZ"},
            {"id": "age_under_40", "weight": 10, "description": "Age under 40"},
            {"id": "complete_documentation", "weight": 20, "description": "All required documents prepared"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Document descriptions (human-friendly labels for UI)
# ---------------------------------------------------------------------------
DOCUMENT_LABELS: dict[str, str] = {
    "valid_passport": "Valid passport (6+ months remaining)",
    "i20": "Form I-20 from your school",
    "sevis_fee_receipt": "SEVIS I-901 fee payment receipt",
    "ds160_confirmation": "DS-160 nonimmigrant visa application confirmation",
    "financial_evidence": "Financial evidence (bank statements, scholarship letter, sponsor affidavit)",
    "academic_transcripts": "Academic transcripts (translated into English if needed)",
    "standardized_test_scores": "Standardized test scores (TOEFL, IELTS, GRE, GMAT, SAT, etc.)",
    "school_admission_letter": "Official school admission letter",
    "photo_ds_compliant": "DS-compliant passport photo",
    "bachelors_degree_or_equivalent": "Bachelor's degree or foreign equivalent",
    "resume_cv": "Current resume or CV",
    "employment_offer_letter": "Employment offer letter from US employer",
    "lca_certified": "Certified Labor Condition Application (LCA)",
    "employer_supporting_documents": "Employer supporting documents (financials, org chart)",
    "specialty_occupation_evidence": "Evidence the position is a specialty occupation",
    "employer_employee_relationship_evidence": "Evidence of employer-employee relationship (relevant for third-party placements)",
    "employment_offer_or_itinerary": "Employment offer letter or itinerary of events",
    "advisory_opinion_or_peer_consultation": "Advisory opinion from peer group or labor organization",
    "expert_letters": "Expert letters from independent experts in your field",
    "evidence_of_awards": "Evidence of nationally/internationally recognized awards",
    "evidence_of_publications": "Evidence of scholarly publications",
    "evidence_of_judging": "Evidence of judging others' work",
    "evidence_of_press_coverage": "Evidence of press coverage in major media",
    "evidence_of_high_salary": "Evidence of high salary relative to peers",
    "evidence_of_membership": "Evidence of membership in selective associations",
    "evidence_of_original_contributions": "Evidence of original contributions of major significance",
    "petitioner_us_citizenship_or_lpr_evidence": "Petitioner's USC or LPR evidence (passport, naturalization cert, green card)",
    "marriage_certificate_if_applicable": "Marriage certificate (if applicable)",
    "birth_certificates": "Birth certificates",
    "proof_of_relationship": "Proof of bona fide relationship (photos, joint accounts, lease, etc.)",
    "passport_photos": "Passport-style photos",
    "petitioner_id": "Petitioner's government-issued ID",
    "beneficiary_id": "Beneficiary's government-issued ID",
    "divorce_decrees_if_applicable": "Divorce decrees (if any prior marriages)",
    "financial_support_evidence": "Financial support evidence",
    "i94_record": "I-94 arrival/departure record",
    "approved_i130_or_i140": "Approved I-130 or I-140 notice",
    "birth_certificate": "Birth certificate (translated if needed)",
    "i693_medical_exam": "I-693 medical exam by USCIS-approved civil surgeon",
    "i864_affidavit_of_support": "I-864 Affidavit of Support",
    "current_immigration_status_evidence": "Evidence of current immigration status",
    "tax_returns_3_years": "Tax returns (3 years)",
    "cas_letter": "Confirmation of Acceptance for Studies (CAS) letter",
    "financial_evidence_28_days": "Financial evidence held for 28 consecutive days",
    "tb_test_if_required": "TB test (if required by country)",
    "english_proficiency_certificate": "English proficiency certificate (IELTS, TOEFL, etc.)",
    "academic_qualifications": "Academic qualification certificates",
    "atas_certificate_if_required": "ATAS certificate (if required for sensitive subjects)",
    "parental_consent_if_under_18": "Parental consent (if under 18)",
    "certificate_of_sponsorship": "Certificate of Sponsorship from licensed sponsor",
    "salary_evidence": "Salary / employment contract evidence",
    "criminal_record_certificate_if_required": "Criminal record certificate (if required)",
    "letter_of_acceptance_dli": "Letter of Acceptance from Designated Learning Institution",
    "proof_of_funds_gic": "Proof of funds (GIC, bank statements)",
    "tuition_payment_proof": "Tuition payment proof (first year)",
    "study_plan_letter": "Study plan / Statement of Purpose",
    "language_test_results": "Language test results (IELTS, CELPIP, TEF, TCF)",
    "medical_exam_if_required": "Medical exam (if required)",
    "police_certificate_if_required": "Police certificate (if required)",
    "biometrics_confirmation": "Biometrics enrollment confirmation",
    "ECA_credential_assessment": "Educational Credential Assessment (ECA) report",
    "work_experience_letters": "Work experience reference letters",
    "police_certificates_all_countries": "Police certificates from all countries lived in 6+ months",
    "medical_exam": "IRCC-approved panel physician medical exam",
    "proof_of_funds_if_FSW": "Proof of settlement funds (if applying under FSW)",
    "coe_confirmation_of_enrolment": "Confirmation of Enrolment (CoE)",
    "gte_statement": "Genuine Temporary Entrant (GTE) statement",
    "financial_capacity_evidence": "Financial capacity evidence",
    "english_proficiency_test": "English proficiency test results",
    "oshc_health_cover": "Overseas Student Health Cover (OSHC)",
    "biometrics_if_required": "Biometrics (if required)",
    "nomination_approval": "Nomination approval from sponsoring employer",
    "skills_assessment_if_required": "Skills assessment (if required for occupation)",
    "police_certificates": "Police certificates",
    "health_examination": "Health examination",
    "university_admission_letter": "University admission letter",
    "blocked_account_evidence": "Blocked account (Sperrkonto) evidence",
    "language_proficiency_certificate": "Language proficiency certificate",
    "health_insurance": "German statutory health insurance enrollment",
    "motivation_letter": "Motivation letter / Statement of Purpose",
    "biometric_photos": "Biometric passport photos",
    "employment_contract": "Employment contract",
    "anabin_university_evaluation": "anabin university and degree evaluation",
    "german_health_insurance": "German health insurance enrollment",
    "offer_of_place": "Offer of Place from INZ-approved provider",
    "evidence_of_funds_NZD20K": "Evidence of funds (NZD $20,000+ per year)",
    "acceptable_standard_of_health_certificate": "Acceptable standard of health certificate",
    "qualification_assessment_NZQA": "NZQA qualification assessment",
    "skilled_employment_offer": "Skilled employment offer",
    "experience_letters": "Experience letters from employers",
}


# ---------------------------------------------------------------------------
# IntakeEngineService
# ---------------------------------------------------------------------------

class IntakeEngineService:
    """Adaptive intake engine: drives onboarding for applicants and attorneys.

    Powers six core capabilities:
      1. list_visa_types_for_family — what visa types are available for a goal
      2. get_questionnaire — adaptive questions for a (visa_type, country)
      3. validate_answers — eligibility check against visa rules
      4. get_document_checklist — required docs for the (visa_type, applicant_situation)
      5. score_strength — application strength score with reason chain
      6. detect_red_flags — surface issues before filing
    """

    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}

    # ---------- discovery ----------
    def list_visa_types(self, country: str | None = None, family: str | None = None) -> list[dict]:
        """List all configured visa types, optionally filtered by country/family."""
        result = []
        for key, cfg in VISA_REGISTRY.items():
            if country and cfg["country"] != country.upper():
                continue
            if family and cfg["family"] != family.lower():
                continue
            result.append({
                "visa_type": key,
                "country": cfg["country"],
                "family": cfg["family"],
                "name": cfg["name"],
                "agency": cfg["agency"],
            })
        result.sort(key=lambda r: (r["country"], r["name"]))
        return result

    def get_visa_config(self, visa_type: str) -> dict | None:
        return VISA_REGISTRY.get(visa_type)

    # ---------- questionnaire ----------
    def get_questionnaire(self, visa_type: str) -> dict:
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            raise ValueError(f"Unknown visa type: {visa_type}")
        return {
            "visa_type": visa_type,
            "name": cfg["name"],
            "country": cfg["country"],
            "family": cfg["family"],
            "agency": cfg["agency"],
            "questions": cfg["key_questions"],
            "total_questions": len(cfg["key_questions"]),
        }

    def start_session(self, applicant_id: str, visa_type: str) -> dict:
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            raise ValueError(f"Unknown visa type: {visa_type}")
        session_id = str(uuid.uuid4())
        session = {
            "id": session_id,
            "applicant_id": applicant_id,
            "visa_type": visa_type,
            "country": cfg["country"],
            "answers": {},
            "documents_uploaded": [],
            "current_step": "questionnaire",
            "started_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "completed": False,
        }
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def list_sessions(self, applicant_id: str | None = None) -> list[dict]:
        sessions = list(self._sessions.values())
        if applicant_id:
            sessions = [s for s in sessions if s["applicant_id"] == applicant_id]
        return sessions

    def submit_answers(self, session_id: str, answers: dict) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        session["answers"].update(answers)
        session["updated_at"] = datetime.utcnow().isoformat()
        session["current_step"] = "documents"
        return session

    # ---------- validation ----------
    def validate_answers(self, visa_type: str, answers: dict) -> dict:
        """Run eligibility rules against answers. Returns blocking_issues, warnings, ok."""
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            raise ValueError(f"Unknown visa type: {visa_type}")
        blocking_issues: list[dict] = []
        warnings: list[dict] = []

        # Required-blocking-if-false questions
        for q in cfg["key_questions"]:
            qid = q["id"]
            if q.get("blocking_if_false") and answers.get(qid) is False:
                blocking_issues.append({
                    "question_id": qid,
                    "label": q["label"],
                    "issue": "Eligibility blocker — answer required and currently disqualifying",
                    "severity": "blocking",
                })

        # Custom eligibility rules
        for rule in cfg["eligibility_rules"]:
            ok = self._evaluate_rule(rule["rule"], answers, cfg)
            if not ok:
                blocking_issues.append({
                    "rule": rule["rule"],
                    "issue": rule["message"],
                    "severity": "blocking",
                })

        # Required questions missing
        for q in cfg["key_questions"]:
            if q.get("required") and answers.get(q["id"]) is None:
                warnings.append({
                    "question_id": q["id"],
                    "label": q["label"],
                    "issue": "Required answer missing",
                    "severity": "warning",
                })

        return {
            "visa_type": visa_type,
            "ok": len(blocking_issues) == 0,
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    def _evaluate_rule(self, rule: str, answers: dict, cfg: dict) -> bool:
        """Tiny safe evaluator. Supports:
        - foo == True / False
        - foo in ['a', 'b']
        - min_criteria_count(N)  (counts answered-True for boolean criteria_* fields)
        """
        rule = rule.strip()
        if rule.startswith("min_criteria_count"):
            # min_criteria_count(N) — count truthy criteria_* answers
            try:
                n = int(rule[rule.index("(") + 1 : rule.index(")")])
            except (ValueError, IndexError):
                return True
            count = sum(1 for k, v in answers.items() if k.startswith("criteria_") and bool(v))
            return count >= n
        if " == " in rule:
            left, right = rule.split(" == ", 1)
            left = left.strip()
            right = right.strip()
            actual = answers.get(left)
            if right == "True":
                return actual is True
            if right == "False":
                return actual is False
            return str(actual) == right.strip("'\"")
        if " in " in rule:
            left, right = rule.split(" in ", 1)
            left = left.strip()
            right = right.strip()
            try:
                allowed = [x.strip().strip("'\"") for x in right.strip("[]").split(",")]
            except Exception:
                return True
            actual = answers.get(left)
            return str(actual) in allowed
        return True

    # ---------- document checklist ----------
    def get_document_checklist(self, visa_type: str, answers: dict | None = None) -> dict:
        """Generate a personalized document checklist. Conditional docs are added/removed
        based on applicant answers (e.g., marriage cert only if married)."""
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            raise ValueError(f"Unknown visa type: {visa_type}")
        answers = answers or {}
        items = []
        for doc_id in cfg["base_documents"]:
            label = DOCUMENT_LABELS.get(doc_id, doc_id.replace("_", " ").title())
            conditional = self._is_conditional(doc_id)
            relevant = self._doc_relevant(doc_id, answers)
            if conditional and not relevant:
                continue
            items.append({
                "doc_id": doc_id,
                "label": label,
                "required": not conditional,
                "category": self._doc_category(doc_id),
            })
        return {
            "visa_type": visa_type,
            "total": len(items),
            "items": items,
            "generated_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _is_conditional(doc_id: str) -> bool:
        return any(doc_id.endswith(suffix) for suffix in ("_if_applicable", "_if_required", "_if_FSW"))

    @staticmethod
    def _doc_relevant(doc_id: str, answers: dict) -> bool:
        # Heuristic relevance based on answers — extend as needed.
        if doc_id == "marriage_certificate_if_applicable":
            return answers.get("relationship") == "spouse" or answers.get("marriage_bona_fide") is not None
        if doc_id == "divorce_decrees_if_applicable":
            return bool(answers.get("prior_petitions"))
        if doc_id == "atas_certificate_if_required":
            return bool(answers.get("atas_required"))
        if doc_id == "tb_test_if_required":
            return True  # TB test rules are country-specific; default to relevant
        if doc_id == "police_certificate_if_required":
            return True
        if doc_id == "medical_exam_if_required":
            return True
        if doc_id == "criminal_record_certificate_if_required":
            return True
        if doc_id == "biometrics_if_required":
            return True
        if doc_id == "parental_consent_if_under_18":
            return False  # need DOB to determine; default to off
        if doc_id == "proof_of_funds_if_FSW":
            return True
        return True

    @staticmethod
    def _doc_category(doc_id: str) -> str:
        if "passport" in doc_id or "id" in doc_id or "photo" in doc_id:
            return "identity"
        if "transcript" in doc_id or "academic" in doc_id or "qualification" in doc_id or "degree" in doc_id or "english" in doc_id or "language" in doc_id:
            return "education"
        if "financial" in doc_id or "fund" in doc_id or "salary" in doc_id or "tax" in doc_id or "support" in doc_id or "blocked_account" in doc_id or "gic" in doc_id:
            return "financial"
        if "employment" in doc_id or "lca" in doc_id or "cos" in doc_id or "cas" in doc_id or "coe" in doc_id or "loa" in doc_id or "nomination" in doc_id or "offer" in doc_id or "contract" in doc_id:
            return "sponsor"
        if "medical" in doc_id or "tb" in doc_id or "health" in doc_id or "i693" in doc_id:
            return "health"
        if "police" in doc_id or "criminal" in doc_id:
            return "background"
        if "marriage" in doc_id or "birth" in doc_id or "divorce" in doc_id or "relationship" in doc_id or "parental" in doc_id:
            return "civil"
        if "evidence_of" in doc_id or "expert" in doc_id or "advisory" in doc_id or "specialty" in doc_id:
            return "evidentiary"
        return "supporting"

    # ---------- strength scoring ----------
    def score_strength(self, visa_type: str, answers: dict, factor_overrides: dict | None = None) -> dict:
        """Score application strength (0-100) by summing strength factors that fire.

        Each factor has a weight; sum is normalized by the max possible points so the
        score stays in [0, 100] even when factors are added/removed."""
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            raise ValueError(f"Unknown visa type: {visa_type}")
        factor_overrides = factor_overrides or {}
        max_points = sum(f["weight"] for f in cfg["strength_factors"])
        earned = 0
        present = []
        missing = []
        for f in cfg["strength_factors"]:
            fid = f["id"]
            fires = factor_overrides.get(fid, self._factor_fires(fid, answers, visa_type))
            if fires:
                earned += f["weight"]
                present.append({"id": fid, "weight": f["weight"], "description": f["description"]})
            else:
                missing.append({"id": fid, "weight": f["weight"], "description": f["description"]})
        score = round((earned / max_points) * 100) if max_points else 0
        tier = "excellent" if score >= 85 else "strong" if score >= 70 else "moderate" if score >= 50 else "weak"
        recommendations = self._recommendations(missing, visa_type)
        return {
            "visa_type": visa_type,
            "score": score,
            "tier": tier,
            "earned_points": earned,
            "max_points": max_points,
            "strengths": present,
            "missing_factors": missing,
            "recommendations": recommendations,
            "scored_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def _factor_fires(factor_id: str, answers: dict, visa_type: str) -> bool:
        """Map answers to strength factors. Returns True if the factor 'fires'."""
        a = answers
        # Common factors
        if factor_id == "no_prior_denials":
            return a.get("prior_us_visa_denial") is False or a.get("prior_uk_refusal") is False or a.get("prior_refusal") is False
        if factor_id == "no_prior_refusals":
            return a.get("prior_uk_refusal") is False or a.get("prior_refusal") is False
        if factor_id == "clean_immigration_history":
            return a.get("prior_us_visa_denial") is False and a.get("prior_immigration_violation") is False
        if factor_id == "ties_to_home_country" or factor_id == "ties_to_home":
            return a.get("intent_to_return") is True or a.get("intent_to_leave") is True
        if factor_id == "english_fluency":
            return a.get("english_proficiency") in ("native", "advanced")
        if factor_id == "strong_english":
            return a.get("english_proficiency") in ("native", "advanced") or a.get("english_competent") is True or a.get("english_b2") is True
        if factor_id == "complete_documentation":
            return False  # set externally based on uploads
        if factor_id == "us_masters_or_higher":
            return a.get("us_masters_or_higher") is True
        if factor_id == "selected_in_lottery":
            return a.get("selected_in_lottery") is True
        if factor_id == "lca_certified":
            return a.get("lca_filed") is True
        if factor_id == "wage_level_iii_or_iv":
            return a.get("wage_level") in ("III", "IV")
        if factor_id == "specialty_occupation_clear":
            # Heuristic: bachelor's + LCA filed + wage level II+
            return a.get("has_bachelors_or_higher") is True and a.get("lca_filed") is True and a.get("wage_level") in ("II", "III", "IV")
        if factor_id == "criteria_count_5_plus":
            return sum(1 for k, v in a.items() if k.startswith("criteria_") and v) >= 5
        if factor_id == "criteria_count_4":
            return sum(1 for k, v in a.items() if k.startswith("criteria_") and v) == 4
        if factor_id == "criteria_count_3":
            return sum(1 for k, v in a.items() if k.startswith("criteria_") and v) == 3
        if factor_id == "advisory_opinion":
            return a.get("has_advisory_opinion") is True
        if factor_id == "us_citizen_petitioner":
            return a.get("petitioner_status") == "US_citizen"
        if factor_id == "no_prior_petitions":
            return a.get("prior_petitions") is False
        if factor_id == "clean_inadmissibility":
            return a.get("beneficiary_inadmissible_grounds") is False
        if factor_id == "priority_date_current":
            return a.get("priority_date_current") is True
        if factor_id == "clean_criminal":
            return a.get("criminal_history") is False
        if factor_id == "lawful_status_maintained":
            return a.get("lawful_status_maintained") is True
        if factor_id == "no_public_charge":
            return a.get("public_charge_concern") is False
        # UK
        if factor_id == "salary_above_threshold":
            return a.get("salary_meets_threshold") is True
        if factor_id == "salary_well_above_threshold":
            return a.get("salary_meets_threshold") is True
        if factor_id == "shortage_occupation":
            return a.get("shortage_occupation") is True
        # CA
        if factor_id == "language_clb_9_plus":
            return a.get("language_test_done") is True
        if factor_id == "canadian_experience":
            return a.get("canadian_experience") is True
        if factor_id == "french_bonus":
            return a.get("spouse_french_speaker") is True
        if factor_id == "skilled_experience_3_plus":
            try:
                return float(a.get("years_experience", 0)) >= 3
            except (TypeError, ValueError):
                return False
        if factor_id == "age_25_to_35":
            try:
                return 25 <= float(a.get("age", 0)) <= 35
            except (TypeError, ValueError):
                return False
        if factor_id == "age_under_40":
            try:
                return float(a.get("age", 0)) < 40
            except (TypeError, ValueError):
                return False
        # AU
        if factor_id == "salary_well_above_tsmit":
            return a.get("salary_meets_tsmit") is True
        if factor_id == "occupation_specialist_skills":
            return a.get("occupation_listed") is True
        if factor_id == "5_plus_years_experience":
            return a.get("two_years_experience") is True
        if factor_id == "skills_assessment_complete":
            return a.get("skills_assessment_done") is True
        if factor_id == "strong_gte":
            return a.get("gte_genuine") is True
        # NZ
        if factor_id == "green_list_tier1":
            return a.get("occupation_listed") is True
        # DE
        if factor_id == "german_b2_plus":
            return a.get("language_certified") is True
        if factor_id == "german_proficiency":
            return a.get("language_certified") is True
        return False

    @staticmethod
    def _recommendations(missing: list[dict], visa_type: str) -> list[str]:
        if not missing:
            return ["Application is well-positioned. Focus on documentation accuracy and timeliness."]
        # Top 5 highest-weight missing factors are the most actionable
        top = sorted(missing, key=lambda m: -m["weight"])[:5]
        return [f"Strengthen: {m['description']}" for m in top]

    # ---------- red flag detection ----------
    def detect_red_flags(self, visa_type: str, answers: dict, applicant: dict | None = None) -> list[dict]:
        """Surface issues before filing. Each flag has severity and recommendation."""
        flags: list[dict] = []
        cfg = VISA_REGISTRY.get(visa_type)
        if not cfg:
            return flags
        applicant = applicant or {}

        # Universal red flags
        if answers.get("prior_us_visa_denial"):
            flags.append({
                "severity": "high",
                "code": "PRIOR_DENIAL",
                "issue": "Prior US visa denial on record",
                "recommendation": "Review the denial reason. Address it directly in the new petition with supporting evidence.",
            })
        if answers.get("prior_immigration_violation"):
            flags.append({
                "severity": "high",
                "code": "PRIOR_VIOLATION",
                "issue": "Prior US immigration violation (overstay, status violation)",
                "recommendation": "Disclose fully. Calculate inadmissibility periods. Consider waiver if applicable.",
            })
        if answers.get("criminal_history"):
            flags.append({
                "severity": "high",
                "code": "CRIMINAL_HISTORY",
                "issue": "Criminal history disclosed",
                "recommendation": "Obtain certified court records and police certificates. Analyze inadmissibility under INA 212.",
            })
        if answers.get("public_charge_concern"):
            flags.append({
                "severity": "medium",
                "code": "PUBLIC_CHARGE",
                "issue": "Possible public charge concern",
                "recommendation": "Strengthen I-864 with joint sponsor if needed. Document totality of circumstances.",
            })
        if answers.get("beneficiary_inadmissible_grounds"):
            flags.append({
                "severity": "high",
                "code": "INADMISSIBILITY",
                "issue": "Potential inadmissibility ground identified",
                "recommendation": "Detailed analysis under INA 212 required. Consider waiver eligibility.",
            })

        # Visa-specific
        if visa_type == "H-1B":
            if answers.get("selected_in_lottery") is False:
                flags.append({
                    "severity": "blocking",
                    "code": "NOT_SELECTED_LOTTERY",
                    "issue": "Not selected in H-1B registration lottery",
                    "recommendation": "Cap-exempt path required (university, nonprofit research, or qualifying employer). Otherwise wait for next FY.",
                })
            if answers.get("wage_level") == "I" and answers.get("us_masters_or_higher") is False:
                flags.append({
                    "severity": "medium",
                    "code": "LOW_WAGE_NO_MASTERS",
                    "issue": "Wage Level I + no US master's degree — heightened RFE risk on specialty occupation",
                    "recommendation": "Strengthen specialty-occupation argument; consider higher wage level or US master's pathway.",
                })
        if visa_type == "O-1":
            criteria_count = sum(1 for k, v in answers.items() if k.startswith("criteria_") and v)
            if 0 < criteria_count < 3:
                flags.append({
                    "severity": "blocking",
                    "code": "INSUFFICIENT_CRITERIA",
                    "issue": f"Only {criteria_count} of 8 evidentiary criteria satisfied (minimum 3 required)",
                    "recommendation": "Build evidence on additional criteria — published material, judging, original contributions.",
                })
        if visa_type == "I-485":
            if answers.get("priority_date_current") is False:
                flags.append({
                    "severity": "blocking",
                    "code": "PRIORITY_DATE_NOT_CURRENT",
                    "issue": "Priority date is not current",
                    "recommendation": "Cannot file I-485 until Visa Bulletin shows priority date as current.",
                })
            if answers.get("lawful_status_maintained") is False:
                flags.append({
                    "severity": "high",
                    "code": "STATUS_GAP",
                    "issue": "Gap in lawful immigration status",
                    "recommendation": "Analyze 245(c)/245(k) eligibility. Evaluate consular processing as alternative.",
                })
        if visa_type == "F-1" and answers.get("financial_sufficient") is False:
            flags.append({
                "severity": "blocking",
                "code": "INSUFFICIENT_FUNDS",
                "issue": "Insufficient documented funds for first year",
                "recommendation": "Obtain additional sponsor affidavits or scholarship documentation.",
            })

        # Document gaps (if applicant uploaded list provided)
        uploaded = set(applicant.get("documents_uploaded", []))
        required = {d for d in cfg["base_documents"] if not self._is_conditional(d)}
        missing = required - uploaded
        if missing and applicant.get("documents_uploaded") is not None:
            flags.append({
                "severity": "medium",
                "code": "DOCUMENT_GAPS",
                "issue": f"{len(missing)} required documents not yet uploaded",
                "recommendation": f"Upload: {', '.join(sorted(missing)[:5])}{'...' if len(missing) > 5 else ''}",
            })

        return flags

    # ---------- summary ----------
    def get_intake_summary(self, session_id: str) -> dict:
        """One-shot rollup: validation + checklist + score + flags. Used by the dashboard."""
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")
        visa_type = session["visa_type"]
        answers = session["answers"]
        validation = self.validate_answers(visa_type, answers)
        checklist = self.get_document_checklist(visa_type, answers)
        score = self.score_strength(visa_type, answers)
        flags = self.detect_red_flags(visa_type, answers, applicant={"documents_uploaded": session["documents_uploaded"]})
        return {
            "session_id": session_id,
            "visa_type": visa_type,
            "validation": validation,
            "documents": checklist,
            "strength": score,
            "red_flags": flags,
            "ready_to_file": validation["ok"] and not [f for f in flags if f["severity"] == "blocking"],
            "summary_at": datetime.utcnow().isoformat(),
        }
