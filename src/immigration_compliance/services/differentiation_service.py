"""Tier 2 Differentiation features — what sets Verom apart from every competitor."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta


# ---------------------------------------------------------------------------
# 1. Cross-Country Immigration Strategy Optimizer
# ---------------------------------------------------------------------------

class StrategyOptimizerService:
    """Input employee profile, get ranked visa pathways across multiple countries."""

    _PATHWAYS: dict[str, list[dict]] = {
        "US": [
            {"visa_type": "H-1B", "category": "work", "timeline_months": 8, "cost_min": 4000, "cost_max": 12000, "success_rate": 0.89, "requirements": ["Bachelor's degree", "Specialty occupation", "Employer sponsorship", "Lottery selection"]},
            {"visa_type": "O-1", "category": "work", "timeline_months": 4, "cost_min": 5000, "cost_max": 15000, "success_rate": 0.78, "requirements": ["Extraordinary ability evidence", "Peer group advisory", "3+ criteria met"]},
            {"visa_type": "L-1", "category": "work", "timeline_months": 5, "cost_min": 3000, "cost_max": 10000, "success_rate": 0.85, "requirements": ["1 year employment abroad", "Managerial/specialized knowledge", "Same employer"]},
            {"visa_type": "EB-2 NIW", "category": "green_card", "timeline_months": 18, "cost_min": 8000, "cost_max": 20000, "success_rate": 0.75, "requirements": ["Advanced degree", "National interest argument", "No employer needed"]},
        ],
        "UK": [
            {"visa_type": "Skilled Worker", "category": "work", "timeline_months": 2, "cost_min": 2000, "cost_max": 5000, "success_rate": 0.92, "requirements": ["Certificate of Sponsorship", "GBP 38,700 salary", "English proficiency"]},
            {"visa_type": "Global Talent", "category": "work", "timeline_months": 2, "cost_min": 1500, "cost_max": 3000, "success_rate": 0.70, "requirements": ["Endorsement from approved body", "Exceptional talent/promise"]},
        ],
        "CA": [
            {"visa_type": "Express Entry", "category": "permanent_residence", "timeline_months": 6, "cost_min": 2000, "cost_max": 5000, "success_rate": 0.90, "requirements": ["CRS score ~480+", "Language test", "Education credential assessment"]},
            {"visa_type": "PGWP", "category": "work", "timeline_months": 2, "cost_min": 500, "cost_max": 1500, "success_rate": 0.95, "requirements": ["Canadian degree", "Eligible institution", "Within 180 days of graduation"]},
        ],
        "AU": [
            {"visa_type": "Subclass 482 TSS", "category": "work", "timeline_months": 3, "cost_min": 3000, "cost_max": 7000, "success_rate": 0.88, "requirements": ["Employer nomination", "Skills assessment", "2 years experience"]},
            {"visa_type": "Subclass 189 Skilled Independent", "category": "permanent_residence", "timeline_months": 12, "cost_min": 5000, "cost_max": 10000, "success_rate": 0.80, "requirements": ["Points test 65+", "Skills assessment", "Occupation on list"]},
        ],
        "DE": [
            {"visa_type": "EU Blue Card", "category": "work", "timeline_months": 3, "cost_min": 500, "cost_max": 2000, "success_rate": 0.90, "requirements": ["University degree", "EUR 45,300 salary", "Job offer"]},
            {"visa_type": "Job Seeker Visa", "category": "work", "timeline_months": 2, "cost_min": 300, "cost_max": 1000, "success_rate": 0.85, "requirements": ["University degree", "Sufficient funds", "No job offer needed"]},
        ],
        "NZ": [
            {"visa_type": "Skilled Migrant", "category": "permanent_residence", "timeline_months": 8, "cost_min": 2000, "cost_max": 5000, "success_rate": 0.82, "requirements": ["Points system 160+", "Job offer or skilled employment", "Health and character"]},
        ],
    }

    def optimize(self, applicant_profile: dict) -> list[dict]:
        education = applicant_profile.get("education", "bachelors")
        experience_years = applicant_profile.get("work_experience_years", 3)
        results = []
        for country, pathways in self._PATHWAYS.items():
            for p in pathways:
                reqs_met = []
                reqs_missing = []
                for req in p["requirements"]:
                    if self._check_req(req, applicant_profile):
                        reqs_met.append(req)
                    else:
                        reqs_missing.append(req)
                fit = round((len(reqs_met) / max(len(p["requirements"]), 1)) * 100)
                results.append({
                    "country": country,
                    "visa_type": p["visa_type"],
                    "category": p["category"],
                    "fit_score": fit,
                    "timeline_months": p["timeline_months"],
                    "estimated_cost_range": f"${p['cost_min']:,} - ${p['cost_max']:,}",
                    "success_probability": p["success_rate"],
                    "pros": self._get_pros(country, p["visa_type"]),
                    "cons": self._get_cons(country, p["visa_type"]),
                    "requirements_met": reqs_met,
                    "requirements_missing": reqs_missing,
                })
        results.sort(key=lambda r: r["fit_score"], reverse=True)
        return results

    def compare_countries(self, applicant_profile: dict, countries: list[str]) -> dict:
        all_results = self.optimize(applicant_profile)
        filtered = [r for r in all_results if r["country"] in countries]
        return {"applicant": applicant_profile, "comparison": filtered, "recommended": filtered[0] if filtered else None}

    def get_country_requirements(self, country: str, visa_type: str) -> dict | None:
        for p in self._PATHWAYS.get(country, []):
            if p["visa_type"] == visa_type:
                return {**p, "country": country}
        return None

    def _check_req(self, req: str, profile: dict) -> bool:
        req_lower = req.lower()
        if "bachelor" in req_lower or "degree" in req_lower or "university" in req_lower:
            return profile.get("education", "") in ("bachelors", "masters", "phd")
        if "advanced degree" in req_lower or "master" in req_lower:
            return profile.get("education", "") in ("masters", "phd")
        return True  # Assume met for non-education requirements in demo

    def _get_pros(self, country: str, visa_type: str) -> list[str]:
        pros_map = {
            ("US", "H-1B"): ["Largest job market", "Path to green card", "Dual intent"],
            ("US", "O-1"): ["No lottery", "No cap", "Faster processing"],
            ("UK", "Skilled Worker"): ["Fast processing", "Path to ILR", "No lottery"],
            ("CA", "Express Entry"): ["Direct PR", "No employer needed", "Fast processing"],
            ("DE", "EU Blue Card"): ["Access to EU", "Low cost", "Path to PR in 33 months"],
        }
        return pros_map.get((country, visa_type), ["Viable immigration pathway"])

    def _get_cons(self, country: str, visa_type: str) -> list[str]:
        cons_map = {
            ("US", "H-1B"): ["Lottery uncertainty", "Employer-dependent", "Long green card wait for India/China"],
            ("US", "O-1"): ["High evidentiary bar", "More expensive", "Short validity"],
            ("UK", "Skilled Worker"): ["High salary threshold", "NHS surcharge", "5 year ILR wait"],
            ("CA", "Express Entry"): ["High CRS cutoff", "Language test required", "Lower salaries than US"],
            ("DE", "EU Blue Card"): ["German language helpful", "Lower salaries", "Bureaucratic process"],
        }
        return cons_map.get((country, visa_type), ["Research specific requirements"])


# ---------------------------------------------------------------------------
# 2. Social Media Compliance Audit
# ---------------------------------------------------------------------------

class SocialMediaAuditService:
    """DS-160 social media disclosure compliance (Dec 2025 requirement)."""

    _REQUIRED_PLATFORMS = [
        "Facebook", "Flickr", "Google+", "Instagram", "LinkedIn",
        "Myspace", "Pinterest", "Reddit", "Snapchat", "Tumblr",
        "Twitter/X", "Vine", "YouTube", "VKontakte", "Weibo",
        "QQ", "Douyin/TikTok", "Twitch", "Threads",
    ]

    def audit_profile(self, applicant_id: str, platforms_data: list[dict]) -> dict:
        results = []
        for p in platforms_data:
            risk = "low"
            flags = []
            if p.get("has_political_content"):
                risk = "medium"
                flags.append("Political content detected — review for potential scrutiny")
            if p.get("has_immigration_criticism"):
                risk = "high"
                flags.append("Immigration-critical content may attract attention")
            if p.get("inconsistent_identity"):
                risk = "high"
                flags.append("Name/identity inconsistency between platform and application")
            results.append({
                "platform": p.get("platform", "Unknown"),
                "handle": p.get("handle", ""),
                "risk_level": risk,
                "flagged_content": flags,
                "recommendations": self._recommend(risk),
            })
        overall_risk = "high" if any(r["risk_level"] == "high" for r in results) else "medium" if any(r["risk_level"] == "medium" for r in results) else "low"
        return {
            "applicant_id": applicant_id,
            "platforms_audited": len(results),
            "overall_risk": overall_risk,
            "platform_results": results,
            "audited_at": datetime.utcnow().isoformat(),
        }

    def generate_disclosure_list(self, applicant_id: str, platforms_data: list[dict] | None = None) -> dict:
        entries = []
        if platforms_data:
            for p in platforms_data:
                entries.append({"platform": p["platform"], "identifier": p.get("handle", "")})
        return {
            "applicant_id": applicant_id,
            "ds160_format": True,
            "disclosure_entries": entries,
            "platforms_requiring_disclosure": self._REQUIRED_PLATFORMS,
            "note": "All social media platforms used in the last 5 years must be disclosed on DS-160.",
        }

    def get_required_platforms(self) -> list[str]:
        return self._REQUIRED_PLATFORMS

    def check_consistency(self, ds160_data: dict, actual_profiles: list[dict]) -> dict:
        disclosed = {d["platform"].lower() for d in ds160_data.get("platforms", [])}
        actual = {p["platform"].lower() for p in actual_profiles}
        missing = actual - disclosed
        extra = disclosed - actual
        return {
            "consistent": len(missing) == 0,
            "undisclosed_platforms": list(missing),
            "disclosed_but_not_found": list(extra),
            "risk_level": "high" if missing else "low",
            "recommendation": "Disclose all platforms used in last 5 years" if missing else "Disclosure appears complete",
        }

    def _recommend(self, risk: str) -> list[str]:
        if risk == "high":
            return ["Review and consider removing flagged content before filing", "Discuss with attorney"]
        if risk == "medium":
            return ["Review content for potential concerns", "Ensure profile matches application identity"]
        return ["No action needed"]


# ---------------------------------------------------------------------------
# 3. Regulatory Change Impact Engine
# ---------------------------------------------------------------------------

class RegulatoryImpactEngine:
    """When Federal Register notice publishes, identify every affected case."""

    def __init__(self) -> None:
        self._regulations: dict[str, dict] = {}
        self._subscriptions: dict[str, list[str]] = {}

    def analyze_regulation(self, regulation_data: dict) -> dict:
        reg_id = str(uuid.uuid4())
        analysis = {
            "id": reg_id,
            "title": regulation_data.get("title", ""),
            "federal_register_number": regulation_data.get("fr_number", ""),
            "affected_visa_types": regulation_data.get("affected_visa_types", []),
            "affected_forms": regulation_data.get("affected_forms", []),
            "effective_date": regulation_data.get("effective_date", ""),
            "comment_deadline": regulation_data.get("comment_deadline", ""),
            "impact_summary": regulation_data.get("summary", "Regulation under analysis"),
            "urgency_level": self._assess_urgency(regulation_data),
            "key_changes": regulation_data.get("key_changes", []),
            "analyzed_at": datetime.utcnow().isoformat(),
        }
        self._regulations[reg_id] = analysis
        return analysis

    def find_affected_cases(self, regulation_id: str, cases: list[dict]) -> list[dict]:
        reg = self._regulations.get(regulation_id, {})
        affected_types = set(reg.get("affected_visa_types", []))
        affected_forms = set(reg.get("affected_forms", []))
        affected = []
        for case in cases:
            case_type = case.get("visa_type", "")
            case_forms = set(case.get("forms", []))
            if case_type in affected_types or case_forms & affected_forms:
                affected.append({
                    "case_id": case.get("id", ""),
                    "visa_type": case_type,
                    "impact": "direct",
                    "affected_because": f"Case type {case_type} is directly affected",
                    "urgency": reg.get("urgency_level", "medium"),
                    "action_required": True,
                })
        return affected

    def generate_action_plan(self, regulation_id: str, case_id: str) -> dict:
        return {
            "regulation_id": regulation_id,
            "case_id": case_id,
            "actions": [
                {"step": 1, "action": "Review regulation impact on this case", "deadline": (date.today() + timedelta(days=7)).isoformat(), "status": "pending"},
                {"step": 2, "action": "Update forms if required", "deadline": (date.today() + timedelta(days=14)).isoformat(), "status": "pending"},
                {"step": 3, "action": "Notify client of changes", "deadline": (date.today() + timedelta(days=3)).isoformat(), "status": "pending"},
                {"step": 4, "action": "Adjust filing strategy if needed", "deadline": (date.today() + timedelta(days=21)).isoformat(), "status": "pending"},
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_pending_regulations(self) -> list[dict]:
        return [
            {"title": "H-1B Wage-Based Selection Final Rule", "status": "effective", "effective_date": "2026-03-01", "affected_visa_types": ["H-1B"], "urgency": "high"},
            {"title": "EAD Auto-Extension Elimination", "status": "effective", "effective_date": "2025-10-01", "affected_visa_types": ["EAD"], "urgency": "high"},
            {"title": "DS-160 Social Media Disclosure Expansion", "status": "effective", "effective_date": "2025-12-01", "affected_visa_types": ["H-1B", "H-4", "L-1", "O-1"], "urgency": "medium"},
            {"title": "USCIS Fee Schedule Update FY2026", "status": "pending", "effective_date": "2026-04-01", "affected_visa_types": ["All"], "urgency": "high"},
            {"title": "Proposed EB-5 Integrity Fund Regulations", "status": "comment_period", "comment_deadline": "2026-05-15", "affected_visa_types": ["EB-5"], "urgency": "medium"},
        ]

    def subscribe_to_federal_register(self, visa_types: list[str]) -> dict:
        sub_id = str(uuid.uuid4())
        self._subscriptions[sub_id] = visa_types
        return {"subscription_id": sub_id, "monitoring": visa_types, "status": "active"}

    def _assess_urgency(self, data: dict) -> str:
        eff = data.get("effective_date", "")
        if eff:
            try:
                eff_date = date.fromisoformat(eff)
                days = (eff_date - date.today()).days
                if days <= 30:
                    return "critical"
                if days <= 90:
                    return "high"
            except ValueError:
                pass
        return "medium"


# ---------------------------------------------------------------------------
# 4. Immigration-Aware Compensation Planner
# ---------------------------------------------------------------------------

class CompensationPlannerService:
    """Connect visa strategy to salary decisions."""

    _PREVAILING_WAGES = {
        ("15-1252", "San Francisco-Oakland"): {1: 128960, 2: 155000, 3: 186000, 4: 222000},
        ("15-1252", "New York-Newark"): {1: 118000, 2: 142000, 3: 170000, 4: 204000},
        ("15-1252", "Seattle-Tacoma"): {1: 120000, 2: 145000, 3: 174000, 4: 208000},
        ("15-1252", "Austin-Round Rock"): {1: 98000, 2: 118000, 3: 142000, 4: 170000},
        ("15-1252", "National Average"): {1: 90000, 2: 110000, 3: 135000, 4: 165000},
    }

    _LOTTERY_PROBS = {1: 0.06, 2: 0.12, 3: 0.24, 4: 0.38}

    def analyze_impact(self, employee_data: dict) -> dict:
        salary = employee_data.get("salary", 100000)
        soc = employee_data.get("soc_code", "15-1252")
        area = employee_data.get("msa", "National Average")
        wages = self._PREVAILING_WAGES.get((soc, area), self._PREVAILING_WAGES[("15-1252", "National Average")])
        current_level = self._determine_level(salary, wages)
        recommended_level = min(current_level + 1, 4) if current_level < 3 else current_level
        return {
            "employee_id": employee_data.get("id", ""),
            "current_salary": salary,
            "soc_code": soc,
            "msa": area,
            "current_wage_level": current_level,
            "recommended_wage_level": recommended_level,
            "prevailing_wages": wages,
            "selection_probability_at_current": self._LOTTERY_PROBS[current_level],
            "selection_probability_at_recommended": self._LOTTERY_PROBS[recommended_level],
            "probability_increase": round(self._LOTTERY_PROBS[recommended_level] - self._LOTTERY_PROBS[current_level], 4),
            "salary_increase_needed": max(0, wages[recommended_level] - salary),
            "compliance_gap": max(0, wages[current_level] - salary),
            "roi_analysis": {
                "additional_cost": max(0, wages[recommended_level] - salary),
                "probability_gain": round(self._LOTTERY_PROBS[recommended_level] - self._LOTTERY_PROBS[current_level], 4),
                "expected_value_gain": round((self._LOTTERY_PROBS[recommended_level] - self._LOTTERY_PROBS[current_level]) * salary, 2),
            },
        }

    def optimize_workforce(self, employees: list[dict]) -> dict:
        analyses = [self.analyze_impact(e) for e in employees]
        total_increase = sum(a["salary_increase_needed"] for a in analyses)
        avg_prob_before = sum(a["selection_probability_at_current"] for a in analyses) / max(len(analyses), 1)
        avg_prob_after = sum(a["selection_probability_at_recommended"] for a in analyses) / max(len(analyses), 1)
        return {
            "total_employees": len(analyses),
            "total_salary_increase_needed": total_increase,
            "average_probability_before": round(avg_prob_before, 4),
            "average_probability_after": round(avg_prob_after, 4),
            "expected_additional_selections": round((avg_prob_after - avg_prob_before) * len(analyses), 1),
            "individual_analyses": analyses,
        }

    def get_prevailing_wages(self, soc_code: str, area: str) -> dict | None:
        wages = self._PREVAILING_WAGES.get((soc_code, area))
        if wages:
            return {"soc_code": soc_code, "area": area, "wage_levels": wages}
        return None

    def calculate_roi(self, salary_increase: float, selection_probability_increase: float) -> dict:
        return {
            "annual_cost": salary_increase,
            "probability_gain": selection_probability_increase,
            "expected_value": round(selection_probability_increase * salary_increase * 3, 2),  # 3-year horizon
            "break_even_years": round(1 / max(selection_probability_increase, 0.01), 1),
            "recommendation": "Favorable ROI" if selection_probability_increase > 0.05 else "Marginal ROI — consider other factors",
        }

    def _determine_level(self, salary: float, wages: dict) -> int:
        for level in (4, 3, 2, 1):
            if salary >= wages[level]:
                return level
        return 1


# ---------------------------------------------------------------------------
# 5. Government Data Transparency Dashboard
# ---------------------------------------------------------------------------

class TransparencyDashboardService:
    """Crowdsourced processing times from platform users."""

    def __init__(self) -> None:
        self._data_points: list[dict] = self._seed_data()

    def submit_data_point(self, user_id: str, data: dict) -> dict:
        point = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "form_type": data.get("form_type", "I-129"),
            "service_center": data.get("service_center", ""),
            "filed_date": data.get("filed_date", ""),
            "decision_date": data.get("decision_date", ""),
            "status": data.get("status", "approved"),
            "processing_days": self._calc_days(data.get("filed_date"), data.get("decision_date")),
            "submitted_at": datetime.utcnow().isoformat(),
            "verified": False,
        }
        self._data_points.append(point)
        return point

    def get_community_times(self, form_type: str, service_center: str | None = None) -> dict:
        pts = [p for p in self._data_points if p["form_type"] == form_type and p.get("processing_days")]
        if service_center:
            pts = [p for p in pts if p["service_center"] == service_center]
        if not pts:
            return {"form_type": form_type, "data_points": 0, "message": "No community data yet"}
        days = [p["processing_days"] for p in pts]
        days.sort()
        return {
            "form_type": form_type,
            "service_center": service_center or "All",
            "data_points": len(days),
            "min_days": days[0],
            "max_days": days[-1],
            "median_days": days[len(days) // 2],
            "average_days": round(sum(days) / len(days)),
            "percentile_25": days[len(days) // 4],
            "percentile_75": days[3 * len(days) // 4],
        }

    def get_trends(self, form_type: str) -> list[dict]:
        return [
            {"month": "2025-10", "avg_days": 145, "data_points": 42},
            {"month": "2025-11", "avg_days": 138, "data_points": 56},
            {"month": "2025-12", "avg_days": 152, "data_points": 48},
            {"month": "2026-01", "avg_days": 141, "data_points": 63},
            {"month": "2026-02", "avg_days": 135, "data_points": 71},
            {"month": "2026-03", "avg_days": 128, "data_points": 45},
        ]

    def get_anomalies(self) -> list[dict]:
        return [
            {"form_type": "I-485", "service_center": "NBC", "expected_days": 540, "actual_days": 890, "status": "pending", "anomaly_type": "significantly_delayed"},
            {"form_type": "I-765", "service_center": "Potomac", "expected_days": 150, "actual_days": 320, "status": "pending", "anomaly_type": "significantly_delayed"},
        ]

    def compare_official_vs_community(self, form_type: str) -> dict:
        official = {"I-129": 120, "I-140": 300, "I-485": 540, "I-765": 150}
        community = self.get_community_times(form_type)
        off = official.get(form_type, 180)
        comm = community.get("average_days", off)
        return {
            "form_type": form_type,
            "official_avg_days": off,
            "community_avg_days": comm,
            "difference_days": comm - off,
            "community_more_accurate": abs(comm - off) < 30,
            "note": "Community data tends to be more current than official USCIS estimates.",
        }

    def _calc_days(self, filed: str | None, decided: str | None) -> int | None:
        if not filed or not decided:
            return None
        try:
            return (date.fromisoformat(decided) - date.fromisoformat(filed)).days
        except ValueError:
            return None

    def _seed_data(self) -> list[dict]:
        seeds = []
        base = date(2025, 6, 1)
        for i in range(50):
            filed = base + timedelta(days=i * 5)
            days = 90 + (i % 7) * 15
            seeds.append({
                "id": str(uuid.uuid4()),
                "user_id": f"user-{i}",
                "form_type": "I-129",
                "service_center": "California" if i % 2 == 0 else "Vermont",
                "filed_date": filed.isoformat(),
                "decision_date": (filed + timedelta(days=days)).isoformat(),
                "status": "approved",
                "processing_days": days,
                "submitted_at": datetime.utcnow().isoformat(),
                "verified": True,
            })
        return seeds
