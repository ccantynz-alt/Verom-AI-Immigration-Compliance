"""Global immigration and travel tracking service."""

from __future__ import annotations

import uuid
from datetime import date

from immigration_compliance.models.global_immigration import (
    Country,
    CountryRiskLevel,
    GlobalAssignment,
    GlobalComplianceSummary,
    TravelEntry,
    WorkPermitStatus,
)


# Built-in country profiles
_COUNTRIES: dict[str, dict] = {
    "US": {"name": "United States", "risk_level": "low", "max_business_travel_days": 365, "tax_threshold_days": 183, "common_permit_types": ["H-1B", "L-1", "O-1", "TN", "E-2"]},
    "GB": {"name": "United Kingdom", "risk_level": "low", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Skilled Worker", "Global Talent", "ICT"]},
    "CA": {"name": "Canada", "risk_level": "low", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Work Permit", "LMIA", "ICT"]},
    "DE": {"name": "Germany", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["EU Blue Card", "ICT", "Work Permit"]},
    "FR": {
        "name": "France",
        "region": "Europe",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Talent Passport", "VLS-TS Student", "EU Blue Card"],
        "visa_types": [
            {
                "name": "Talent Passport (Passeport Talent)",
                "category": "work",
                "processing_time": "4-8 weeks",
                "max_duration": "4 years",
                "requirements": [
                    "Master's degree or equivalent for salaried workers",
                    "Employment contract with French employer",
                    "Minimum salary of 1.5x the French annual gross minimum wage (~EUR 39,000/year)",
                    "Valid passport with at least 1 year validity",
                    "Proof of accommodation in France",
                    "Comprehensive health insurance",
                    "No prior immigration violations in Schengen area",
                ],
            },
            {
                "name": "Student Visa (VLS-TS)",
                "category": "student",
                "processing_time": "2-6 weeks",
                "max_duration": "1 year (renewable)",
                "requirements": [
                    "Acceptance letter from a French educational institution",
                    "Proof of sufficient financial resources (~EUR 615/month)",
                    "Campus France registration and interview",
                    "Valid passport",
                    "Proof of accommodation in France",
                    "Health insurance coverage",
                    "Academic transcripts and diplomas",
                    "French or English language proficiency (depending on program)",
                ],
            },
            {
                "name": "EU Blue Card (Carte Bleue Europeenne)",
                "category": "work",
                "processing_time": "6-10 weeks",
                "max_duration": "4 years",
                "requirements": [
                    "Higher education qualification (at least 3 years of study)",
                    "Employment contract of at least 1 year with French employer",
                    "Minimum annual gross salary of 1.5x the average national salary (~EUR 53,837/year)",
                    "Job must match qualification field",
                    "Valid passport",
                    "Clean criminal record",
                    "Proof of accommodation in France",
                ],
            },
        ],
    },
    "JP": {
        "name": "Japan",
        "region": "Asia-Pacific",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Engineer/Specialist in Humanities/International Services", "Student", "Specified Skilled Worker"],
        "visa_types": [
            {
                "name": "Engineer/Specialist in Humanities/International Services",
                "category": "work",
                "processing_time": "1-3 months",
                "max_duration": "5 years",
                "requirements": [
                    "Bachelor's degree or equivalent in a relevant field, OR 10+ years of professional experience",
                    "Employment contract with a Japanese company (sponsoring employer)",
                    "Salary comparable to Japanese nationals in equivalent positions",
                    "Job duties must correspond to engineering, humanities, or international services",
                    "Certificate of Eligibility (CoE) issued by Immigration Services Agency",
                    "Valid passport",
                    "No criminal record or prior deportation from Japan",
                ],
            },
            {
                "name": "Student Visa (Ryugaku)",
                "category": "student",
                "processing_time": "2-8 weeks",
                "max_duration": "4 years 3 months",
                "requirements": [
                    "Acceptance letter from a Japanese educational institution",
                    "Proof of sufficient funds to cover living expenses (~JPY 200,000/month)",
                    "Certificate of Eligibility (CoE) issued by sponsoring institution",
                    "Valid passport",
                    "Academic transcripts from previous education",
                    "Japanese language proficiency certificate (JLPT N2 or above recommended for Japanese-medium programs)",
                    "Health certificate may be required",
                ],
            },
            {
                "name": "Specified Skilled Worker (Tokutei Gino)",
                "category": "work",
                "processing_time": "1-3 months",
                "max_duration": "5 years (Type 1) or unlimited (Type 2)",
                "requirements": [
                    "Pass industry-specific skills examination",
                    "Pass Japanese Language Proficiency Test (JLPT N4 or above)",
                    "Employment contract with a registered Japanese employer",
                    "Certificate of Eligibility (CoE)",
                    "Applicable to 16 designated industry sectors (nursing care, construction, agriculture, etc.)",
                    "Valid passport",
                    "No prior immigration violations in Japan",
                    "Type 2 requires advanced skills exam and allows family dependents",
                ],
            },
        ],
    },
    "AU": {"name": "Australia", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["TSS 482", "ENS 186", "Business 408"]},
    "SG": {
        "name": "Singapore",
        "region": "Asia-Pacific",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Employment Pass", "S Pass", "EntrePass"],
        "visa_types": [
            {
                "name": "Employment Pass (EP)",
                "category": "work",
                "processing_time": "3-8 weeks",
                "max_duration": "2 years (initial), 3 years (renewal)",
                "requirements": [
                    "Minimum fixed monthly salary of SGD 5,600 (higher for experienced candidates and financial services sector: SGD 6,200)",
                    "Recognized university degree or professional qualifications",
                    "Relevant work experience for the role",
                    "Job offer from a Singapore-registered employer",
                    "Employer must meet Fair Consideration Framework (FCF) advertising requirements",
                    "COMPASS framework points-based assessment (salary, qualifications, diversity, support for local employment)",
                    "Valid passport with at least 6 months validity",
                ],
            },
            {
                "name": "S Pass",
                "category": "work",
                "processing_time": "3-8 weeks",
                "max_duration": "2 years",
                "requirements": [
                    "Minimum fixed monthly salary of SGD 3,150 (higher for experienced candidates and financial services sector)",
                    "Diploma or degree from an accredited institution",
                    "Relevant work experience",
                    "Job offer from a Singapore-registered employer",
                    "Employer must comply with S Pass quota (max 10-18% of workforce depending on sector)",
                    "Employer must pay monthly foreign worker levy",
                    "Valid passport",
                ],
            },
            {
                "name": "EntrePass",
                "category": "entrepreneur",
                "processing_time": "8-12 weeks",
                "max_duration": "1 year (initial), 2 years (renewal)",
                "requirements": [
                    "Must be starting or have started a private limited company registered with ACRA",
                    "Company must be registered for less than 6 months at time of application (or not yet registered)",
                    "Minimum paid-up capital of SGD 50,000",
                    "Meet at least one innovation criterion: venture-backed, incubator-affiliated, IP ownership, or significant R&D expenditure",
                    "Detailed business plan",
                    "Valid passport",
                    "Renewal requires meeting progressive milestones (local employment, revenue, investment raised)",
                ],
            },
        ],
    },
    "IN": {"name": "India", "risk_level": "medium", "max_business_travel_days": 180, "tax_threshold_days": 182, "common_permit_types": ["Employment Visa", "Business Visa"]},
    "CN": {"name": "China", "risk_level": "medium", "max_business_travel_days": 30, "tax_threshold_days": 183, "common_permit_types": ["Z Visa / Work Permit", "R Visa"]},
    "BR": {"name": "Brazil", "risk_level": "medium", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["Work Visa (VITEM V)", "Technical Visa"]},
    "AE": {
        "name": "United Arab Emirates",
        "region": "Middle East",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Golden Visa", "Employment Visa", "Green Visa"],
        "visa_types": [
            {
                "name": "Golden Visa",
                "category": "long-term residency",
                "processing_time": "2-4 weeks",
                "max_duration": "10 years (renewable)",
                "requirements": [
                    "Must qualify under one eligible category: investor, entrepreneur, specialized talent, researcher, or outstanding student",
                    "Investors: minimum AED 2 million in property or business investment",
                    "Entrepreneurs: own a project with minimum capital of AED 500,000 or approval from an accredited incubator",
                    "Specialized talent: professionals in engineering, science, health, education, technology, or culture with relevant endorsements",
                    "Valid passport with at least 6 months validity",
                    "Medical fitness certificate from UAE-approved facility",
                    "UAE health insurance",
                    "No criminal record",
                    "Allows sponsorship of spouse, children, and domestic helpers",
                ],
            },
            {
                "name": "Employment Visa (Work Permit)",
                "category": "work",
                "processing_time": "2-4 weeks",
                "max_duration": "2-3 years (renewable)",
                "requirements": [
                    "Valid job offer from a UAE-registered employer",
                    "Employer must hold a valid trade license",
                    "Employment contract approved by Ministry of Human Resources (MOHRE)",
                    "Medical fitness test at UAE-approved medical center",
                    "Emirates ID registration",
                    "Valid passport with at least 6 months validity",
                    "Attested educational certificates (for skilled positions)",
                    "Entry permit issued before travel to UAE",
                    "Status change possible for those already in UAE on visit visa",
                ],
            },
            {
                "name": "Green Visa",
                "category": "self-sponsored residency",
                "processing_time": "2-4 weeks",
                "max_duration": "5 years (renewable)",
                "requirements": [
                    "Must qualify under one eligible category: skilled employee, freelancer/self-employed, or investor",
                    "Skilled employees: minimum salary of AED 15,000/month and bachelor's degree or equivalent",
                    "Freelancers: valid freelance/self-employment permit from MOHRE and annual income of AED 360,000 or more",
                    "Investors: partner or shareholder in a UAE commercial entity",
                    "Valid passport with at least 6 months validity",
                    "Medical fitness certificate",
                    "UAE health insurance",
                    "No employer sponsorship required (self-sponsored)",
                    "6-month grace period to remain in UAE after visa expiry",
                ],
            },
        ],
    },
    "NL": {
        "name": "Netherlands",
        "region": "Europe",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Highly Skilled Migrant (Kennismigrant)", "Orientation Year (Zoekjaar)", "EU Blue Card"],
        "visa_types": [
            {
                "name": "Highly Skilled Migrant (Kennismigrant)",
                "category": "work",
                "processing_time": "2-4 weeks",
                "max_duration": "5 years (tied to employment contract duration)",
                "requirements": [
                    "Employment contract with a recognized IND sponsor (employer must be registered as sponsor)",
                    "Minimum gross monthly salary of EUR 5,008 (age 30+) or EUR 3,672 (under 30) — thresholds updated annually",
                    "Salary threshold reduced for graduates of Dutch or top-200 universities within 3 years of graduation",
                    "Valid passport",
                    "Employer handles application via IND sponsor portal",
                    "No tuberculosis screening certificate required for EU/EEA nationals; required for others from high-risk countries",
                    "Health insurance mandatory upon arrival",
                    "May qualify for 30% tax ruling (tax-free allowance on salary)",
                ],
            },
            {
                "name": "Orientation Year (Zoekjaar)",
                "category": "post-study/job search",
                "processing_time": "2-4 weeks",
                "max_duration": "1 year",
                "requirements": [
                    "Graduated from a Dutch educational institution within the last 3 years, OR",
                    "Graduated from a top-200 university (Times Higher Education, QS, or Shanghai ranking) within the last 3 years, OR",
                    "Completed scientific research in the Netherlands as a PhD candidate",
                    "Valid passport",
                    "Proof of degree completion",
                    "Sufficient funds to support oneself during the search year",
                    "Allows unrestricted employment without separate work permit during the orientation year",
                    "Cannot be extended — must transition to another permit type (e.g., Kennismigrant) before expiry",
                ],
            },
            {
                "name": "EU Blue Card (Netherlands)",
                "category": "work",
                "processing_time": "4-6 weeks",
                "max_duration": "4 years",
                "requirements": [
                    "Higher education qualification (at least 3 years of study at a recognized institution)",
                    "Employment contract of at least 1 year with a Dutch employer",
                    "Minimum gross annual salary of EUR 67,885 (2024/2025 threshold — adjusted annually)",
                    "Job must match the field of qualification",
                    "Employer must be registered as IND recognized sponsor",
                    "Valid passport",
                    "No criminal record",
                    "Tuberculosis screening for nationals of designated countries",
                    "After 33 months of Blue Card employment, eligible for EU long-term resident status",
                ],
            },
        ],
    },
    "IE": {
        "name": "Ireland",
        "region": "Europe",
        "risk_level": "low",
        "max_business_travel_days": 90,
        "tax_threshold_days": 183,
        "common_permit_types": ["Stamp 1 (Work)", "Stamp 2 (Student)", "Critical Skills Employment Permit"],
        "visa_types": [
            {
                "name": "Stamp 1 (Work)",
                "category": "work",
                "processing_time": "4-12 weeks",
                "max_duration": "2 years (renewable)",
                "requirements": [
                    "Valid employment permit (General Employment Permit or other qualifying permit)",
                    "Employment contract with an Irish employer",
                    "Minimum annual salary of EUR 34,000 for General Employment Permit",
                    "Role must not be on the Ineligible List of Occupations",
                    "Employer must demonstrate labour market needs test (advertised role for 28 days)",
                    "Valid passport with at least 12 months validity",
                    "Private health insurance",
                    "No criminal record",
                    "Registration with local immigration office (Garda National Immigration Bureau)",
                ],
            },
            {
                "name": "Stamp 2 (Student)",
                "category": "student",
                "processing_time": "2-8 weeks",
                "max_duration": "2 years (language courses) or duration of degree program (up to 7 years total)",
                "requirements": [
                    "Acceptance on a full-time course at an approved Irish educational institution listed on ILEP",
                    "Course must be at least 15 hours per week",
                    "Proof of tuition fees paid (or evidence of scholarship/sponsorship)",
                    "Proof of sufficient funds: EUR 10,000 in a personal bank account",
                    "Private medical insurance covering the duration of stay",
                    "Valid passport",
                    "Allows part-time work up to 20 hours/week during term, 40 hours/week during holidays",
                    "Must attend at least 85% of classes",
                    "Registration with local immigration office upon arrival",
                ],
            },
            {
                "name": "Critical Skills Employment Permit",
                "category": "work",
                "processing_time": "4-8 weeks",
                "max_duration": "2 years (eligible for Stamp 4 after 2 years)",
                "requirements": [
                    "Job offer in an occupation on the Critical Skills Occupations List",
                    "Minimum annual salary of EUR 38,000 for roles on the Critical Skills List",
                    "For occupations not on the list but with salary above EUR 64,000, may still qualify",
                    "Relevant degree or higher qualification (minimum QQI Level 7 or equivalent)",
                    "Employment contract of at least 2 years duration",
                    "Valid passport with at least 12 months validity",
                    "No labour market needs test required (exempt)",
                    "Spouse/partner eligible for Stamp 1G (immediate work rights without separate permit)",
                    "After 2 years, eligible for Stamp 4 (unrestricted work permission)",
                ],
            },
        ],
    },
    "KR": {"name": "South Korea", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["E-7", "D-7", "D-8"]},
    "MX": {"name": "Mexico", "risk_level": "medium", "max_business_travel_days": 180, "tax_threshold_days": 183, "common_permit_types": ["Temporary Resident Work Visa"]},
    "IL": {"name": "Israel", "risk_level": "medium", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["B-1 Work Visa", "Expert Visa"]},
    "CH": {"name": "Switzerland", "risk_level": "low", "max_business_travel_days": 90, "tax_threshold_days": 183, "common_permit_types": ["L Permit", "B Permit"]},
}


class GlobalImmigrationService:
    """Manages global assignments, travel tracking, and multi-country compliance."""

    def __init__(self) -> None:
        self._assignments: dict[str, GlobalAssignment] = {}
        self._travel: dict[str, TravelEntry] = {}

    def get_countries(self) -> list[Country]:
        return [
            Country(
                code=code,
                name=data["name"],
                risk_level=CountryRiskLevel(data["risk_level"]),
                max_business_travel_days=data["max_business_travel_days"],
                tax_threshold_days=data["tax_threshold_days"],
                common_permit_types=data["common_permit_types"],
            )
            for code, data in sorted(_COUNTRIES.items(), key=lambda x: x[1]["name"])
        ]

    def get_country(self, code: str) -> Country | None:
        data = _COUNTRIES.get(code.upper())
        if data is None:
            return None
        return Country(
            code=code.upper(),
            name=data["name"],
            risk_level=CountryRiskLevel(data["risk_level"]),
            max_business_travel_days=data["max_business_travel_days"],
            tax_threshold_days=data["tax_threshold_days"],
            common_permit_types=data["common_permit_types"],
        )

    # Assignments
    def create_assignment(self, assignment: GlobalAssignment) -> GlobalAssignment:
        self._assignments[assignment.id] = assignment
        return assignment

    def get_assignments(self, employee_id: str | None = None) -> list[GlobalAssignment]:
        assignments = list(self._assignments.values())
        if employee_id:
            assignments = [a for a in assignments if a.employee_id == employee_id]
        return assignments

    def delete_assignment(self, assignment_id: str) -> bool:
        return self._assignments.pop(assignment_id, None) is not None

    # Travel
    def add_travel(self, entry: TravelEntry) -> TravelEntry:
        if entry.entry_date and entry.exit_date:
            entry.days_counted = (entry.exit_date - entry.entry_date).days + 1
        self._travel[entry.id] = entry
        return entry

    def get_travel(self, employee_id: str | None = None) -> list[TravelEntry]:
        entries = list(self._travel.values())
        if employee_id:
            entries = [t for t in entries if t.employee_id == employee_id]
        return sorted(entries, key=lambda t: t.entry_date, reverse=True)

    def delete_travel(self, entry_id: str) -> bool:
        return self._travel.pop(entry_id, None) is not None

    # Compliance summary
    def get_compliance_summary(self, employee_id: str) -> GlobalComplianceSummary:
        assignments = self.get_assignments(employee_id)
        travel = self.get_travel(employee_id)

        # Aggregate days by country
        country_days: dict[str, int] = {}
        for t in travel:
            country_days[t.country_code] = country_days.get(t.country_code, 0) + t.days_counted

        risk_countries = []
        tax_risk = []
        expiring = []

        for a in assignments:
            country = _COUNTRIES.get(a.country_code, {})
            if a.days_remaining is not None and 0 < a.days_remaining <= 90:
                expiring.append(a)
            total_days = country_days.get(a.country_code, 0) + a.days_in_country
            threshold = country.get("tax_threshold_days", 183)
            if total_days >= threshold:
                tax_risk.append(a.country_name)
            max_days = country.get("max_business_travel_days", 90)
            if total_days > max_days:
                risk_countries.append(a.country_name)

        return GlobalComplianceSummary(
            employee_id=employee_id,
            assignments=assignments,
            travel_history=travel,
            countries_with_risk=risk_countries,
            total_countries_active=len({a.country_code for a in assignments}),
            tax_risk_countries=tax_risk,
            permit_expiring_soon=expiring,
        )
