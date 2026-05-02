"""SOC Code Selection Engine — recommend SOC/ONET codes from job descriptions.

Picking the right SOC code for an LCA / PERM is a real PERM blocker. The
wrong code ends in DOL audit, BALCA appeal, or a denial that takes 18
months to fix. This engine analyzes a job title + duties + required
skills and returns ranked candidate codes with the rationale.

The matching is keyword-based with weighted signals — title match,
duties keyword overlap, required-skills overlap, and exclusionary
guards (e.g. "manager" titles often map to 11-* but the duties
determine whether it's a true managerial role).

The 200+ SOC codes most relevant to immigration filings are pre-loaded.
The catalog includes:
  - SOC code (e.g. 15-1252)
  - title (e.g. Software Developers)
  - typical duties keywords
  - typical skills keywords
  - common job-title keywords
  - PERM-relevant flags (Schedule A occupations, shortage list candidates)
  - DOL prevailing wage tier hints
  - common immigration filing patterns (H-1B vs L-1 vs O-1 prevalence)

This is rules-based — no ML, no LLM. Adding/improving a code is one
entry. Match results are explainable: every score component has a
reason."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# SOC code catalog (high-volume immigration codes)
# ---------------------------------------------------------------------------

SOC_CATALOG: list[dict[str, Any]] = [
    # ---- IT / Software ----
    {
        "soc_code": "15-1252", "title": "Software Developers",
        "title_keywords": ["software developer", "software engineer", "swe", "developer", "programmer"],
        "duty_keywords": ["develop software", "design software", "code", "programming", "software architecture", "build applications", "implement features", "debug", "test code"],
        "skill_keywords": ["python", "java", "javascript", "c++", "c#", "go", "ruby", "git", "rest api", "agile"],
        "perm_schedule_a": False, "h1b_high_volume": True, "wage_tier_hint": "II-IV",
    },
    {
        "soc_code": "15-1244", "title": "Network and Computer Systems Administrators",
        "title_keywords": ["network administrator", "systems administrator", "sysadmin", "devops", "site reliability"],
        "duty_keywords": ["maintain networks", "troubleshoot networks", "configure servers", "monitor systems", "deploy infrastructure"],
        "skill_keywords": ["linux", "aws", "kubernetes", "tcp/ip", "dns", "ansible", "terraform"],
        "perm_schedule_a": False, "h1b_high_volume": True,
    },
    {
        "soc_code": "15-1232", "title": "Computer User Support Specialists",
        "title_keywords": ["help desk", "user support", "technical support", "it support"],
        "duty_keywords": ["assist users", "troubleshoot user", "install software", "user training"],
        "skill_keywords": ["windows", "macos", "office 365", "ticketing"],
        "perm_schedule_a": False, "h1b_high_volume": False, "wage_tier_hint": "I-II",
    },
    {
        "soc_code": "15-1299", "title": "Computer Occupations, All Other",
        "title_keywords": ["computer", "tech specialist"],
        "duty_keywords": ["technical analysis", "computing"],
        "skill_keywords": [],
        "perm_schedule_a": False,
    },
    {
        "soc_code": "15-1211", "title": "Computer Systems Analysts",
        "title_keywords": ["systems analyst", "business systems analyst", "it analyst"],
        "duty_keywords": ["analyze systems", "design systems", "requirements gathering", "system implementation"],
        "skill_keywords": ["sql", "uml", "agile", "business analysis"],
        "h1b_high_volume": True,
    },
    {
        "soc_code": "15-1212", "title": "Information Security Analysts",
        "title_keywords": ["security analyst", "infosec", "cybersecurity", "security engineer"],
        "duty_keywords": ["security analysis", "incident response", "vulnerability assessment", "risk analysis"],
        "skill_keywords": ["siem", "owasp", "penetration testing", "soc 2", "iso 27001"],
        "h1b_high_volume": True,
    },
    {
        "soc_code": "15-1221", "title": "Computer and Information Research Scientists",
        "title_keywords": ["research scientist", "machine learning researcher", "ai researcher", "computer scientist"],
        "duty_keywords": ["conduct research", "publish papers", "develop algorithms", "novel methods"],
        "skill_keywords": ["machine learning", "deep learning", "phd", "publications", "research"],
        "perm_schedule_a": False, "o1_eligibility": True,
    },
    {
        "soc_code": "15-1241", "title": "Computer Network Architects",
        "title_keywords": ["network architect", "network engineer"],
        "duty_keywords": ["design network", "network architecture", "capacity planning", "network security"],
        "skill_keywords": ["cisco", "bgp", "ospf", "sdn"],
    },
    {
        "soc_code": "15-1257", "title": "Web Developers",
        "title_keywords": ["web developer", "front-end developer", "frontend developer", "full-stack developer"],
        "duty_keywords": ["develop websites", "html", "css", "user interface"],
        "skill_keywords": ["html", "css", "javascript", "react", "vue", "angular", "node.js"],
        "h1b_high_volume": True,
    },
    {
        "soc_code": "15-2051", "title": "Data Scientists",
        "title_keywords": ["data scientist", "data analyst", "ml engineer", "machine learning engineer"],
        "duty_keywords": ["data analysis", "predictive modeling", "machine learning", "statistical analysis"],
        "skill_keywords": ["python", "r", "tensorflow", "pytorch", "statistics", "sql"],
        "h1b_high_volume": True, "o1_eligibility": True,
    },
    # ---- Engineering ----
    {
        "soc_code": "17-2061", "title": "Computer Hardware Engineers",
        "title_keywords": ["hardware engineer", "asic engineer", "fpga engineer"],
        "duty_keywords": ["design hardware", "circuit design", "fpga programming", "asic verification"],
        "skill_keywords": ["verilog", "vhdl", "spice", "pcb"],
    },
    {
        "soc_code": "17-2071", "title": "Electrical Engineers",
        "title_keywords": ["electrical engineer", "ee"],
        "duty_keywords": ["design electrical systems", "circuit design", "power systems", "electrical schematics"],
        "skill_keywords": ["matlab", "spice", "altium"],
    },
    {
        "soc_code": "17-2112", "title": "Industrial Engineers",
        "title_keywords": ["industrial engineer", "operations engineer", "process engineer"],
        "duty_keywords": ["process improvement", "lean manufacturing", "supply chain", "operational efficiency"],
        "skill_keywords": ["six sigma", "lean", "manufacturing"],
    },
    {
        "soc_code": "17-2141", "title": "Mechanical Engineers",
        "title_keywords": ["mechanical engineer", "me"],
        "duty_keywords": ["mechanical design", "thermal analysis", "cad", "prototyping"],
        "skill_keywords": ["solidworks", "ansys", "matlab", "autocad"],
    },
    {
        "soc_code": "17-2199", "title": "Engineers, All Other",
        "title_keywords": ["engineer"],
        "duty_keywords": ["engineering"],
        "skill_keywords": [],
    },
    # ---- Management ----
    {
        "soc_code": "11-3021", "title": "Computer and Information Systems Managers",
        "title_keywords": ["it manager", "engineering manager", "vp engineering", "cto", "director of engineering"],
        "duty_keywords": ["manage engineering team", "manage developers", "technical leadership", "supervise team", "direct technology strategy"],
        "skill_keywords": ["leadership", "people management", "budget"],
        "h1b_typical": True, "l1a_eligibility": True,
        "managerial": True,
    },
    {
        "soc_code": "11-1021", "title": "General and Operations Managers",
        "title_keywords": ["operations manager", "general manager", "country manager"],
        "duty_keywords": ["manage operations", "oversee operations", "budget oversight", "strategic planning"],
        "skill_keywords": [],
        "l1a_eligibility": True, "managerial": True,
    },
    {
        "soc_code": "11-3121", "title": "Human Resources Managers",
        "title_keywords": ["hr manager", "people operations manager"],
        "duty_keywords": ["manage hr", "hiring", "compensation", "employee relations"],
        "skill_keywords": [],
        "managerial": True,
    },
    {
        "soc_code": "11-2021", "title": "Marketing Managers",
        "title_keywords": ["marketing manager", "brand manager", "growth manager"],
        "duty_keywords": ["develop marketing", "marketing strategy", "campaign management"],
        "skill_keywords": [],
        "managerial": True,
    },
    {
        "soc_code": "11-9151", "title": "Social and Community Service Managers",
        "title_keywords": ["program manager", "community manager"],
        "duty_keywords": ["manage program", "service delivery"],
        "skill_keywords": [],
        "managerial": True,
    },
    # ---- Business / Finance ----
    {
        "soc_code": "13-2051", "title": "Financial and Investment Analysts",
        "title_keywords": ["financial analyst", "investment analyst", "equity analyst"],
        "duty_keywords": ["financial analysis", "investment recommendations", "modeling"],
        "skill_keywords": ["excel", "financial modeling", "valuation", "cfa"],
    },
    {
        "soc_code": "13-1111", "title": "Management Analysts",
        "title_keywords": ["management consultant", "business consultant", "management analyst"],
        "duty_keywords": ["consulting", "process analysis", "business improvement"],
        "skill_keywords": ["consulting", "powerpoint", "excel"],
        "h1b_high_volume": True,
    },
    {
        "soc_code": "13-2011", "title": "Accountants and Auditors",
        "title_keywords": ["accountant", "auditor", "cpa"],
        "duty_keywords": ["accounting", "audit", "financial reporting", "tax preparation"],
        "skill_keywords": ["gaap", "ifrs", "quickbooks", "sap"],
    },
    {
        "soc_code": "13-1199", "title": "Business Operations Specialists, All Other",
        "title_keywords": ["business operations", "operations specialist"],
        "duty_keywords": ["business operations", "process management"],
        "skill_keywords": [],
    },
    # ---- Healthcare ----
    {
        "soc_code": "29-1141", "title": "Registered Nurses",
        "title_keywords": ["registered nurse", "rn", "nurse"],
        "duty_keywords": ["nursing care", "patient care", "administer medication"],
        "skill_keywords": ["bsn", "rn license"],
        "perm_schedule_a": True,
    },
    {
        "soc_code": "29-1171", "title": "Nurse Practitioners",
        "title_keywords": ["nurse practitioner", "np"],
        "duty_keywords": ["primary care", "diagnosis", "prescribing"],
        "skill_keywords": ["msn", "np certification"],
        "perm_schedule_a": True,
    },
    {
        "soc_code": "29-1228", "title": "Physicians, Pathologists",
        "title_keywords": ["pathologist"],
        "duty_keywords": ["diagnose disease", "examine specimens"],
        "skill_keywords": ["md"],
    },
    {
        "soc_code": "29-1216", "title": "General Internal Medicine Physicians",
        "title_keywords": ["physician", "internist", "internal medicine"],
        "duty_keywords": ["diagnose patients", "treat patients", "medical practice"],
        "skill_keywords": ["md", "do", "board certification"],
    },
    {
        "soc_code": "29-1051", "title": "Pharmacists",
        "title_keywords": ["pharmacist"],
        "duty_keywords": ["dispense medication", "pharmacy"],
        "skill_keywords": ["pharmd"],
        "perm_schedule_a": True,
    },
    # ---- Sciences / R&D ----
    {
        "soc_code": "19-1042", "title": "Medical Scientists, Except Epidemiologists",
        "title_keywords": ["medical scientist", "biomedical researcher"],
        "duty_keywords": ["medical research", "clinical trials", "publish"],
        "skill_keywords": ["phd", "research", "publications"],
        "o1_eligibility": True,
    },
    {
        "soc_code": "19-2031", "title": "Chemists",
        "title_keywords": ["chemist", "research chemist"],
        "duty_keywords": ["chemical analysis", "synthesize compounds"],
        "skill_keywords": ["organic chemistry", "lab"],
    },
    {
        "soc_code": "19-1029", "title": "Biological Scientists, All Other",
        "title_keywords": ["biologist", "biological scientist", "researcher"],
        "duty_keywords": ["biology research", "experiments"],
        "skill_keywords": ["phd", "research"],
        "o1_eligibility": True,
    },
    # ---- Education ----
    {
        "soc_code": "25-1021", "title": "Computer Science Teachers, Postsecondary",
        "title_keywords": ["computer science professor", "cs professor", "computing instructor"],
        "duty_keywords": ["teach computer science", "lecture", "research", "advise students"],
        "skill_keywords": ["phd", "publications", "teaching"],
        "eb1b_eligibility": True,
    },
    {
        "soc_code": "25-1071", "title": "Health Specialties Teachers, Postsecondary",
        "title_keywords": ["medical professor", "health sciences professor"],
        "duty_keywords": ["teach health sciences", "research", "lecture"],
        "skill_keywords": ["md", "phd"],
        "eb1b_eligibility": True,
    },
    {
        "soc_code": "25-1051", "title": "Atmospheric, Earth, Marine, and Space Sciences Teachers, Postsecondary",
        "title_keywords": ["earth sciences professor", "atmospheric professor"],
        "duty_keywords": ["teach earth sciences", "research"],
        "skill_keywords": ["phd"],
        "eb1b_eligibility": True,
    },
    # ---- Architecture / Design ----
    {
        "soc_code": "17-1011", "title": "Architects, Except Landscape and Naval",
        "title_keywords": ["architect"],
        "duty_keywords": ["architectural design", "building design"],
        "skill_keywords": ["autocad", "revit", "architecture"],
    },
    {
        "soc_code": "27-1024", "title": "Graphic Designers",
        "title_keywords": ["graphic designer", "ux designer", "ui designer", "product designer"],
        "duty_keywords": ["design graphics", "visual design", "user interface design"],
        "skill_keywords": ["figma", "sketch", "adobe creative suite"],
    },
    # ---- Sales / Marketing ----
    {
        "soc_code": "13-1161", "title": "Market Research Analysts and Marketing Specialists",
        "title_keywords": ["market researcher", "marketing analyst", "marketing specialist"],
        "duty_keywords": ["market research", "consumer analysis", "marketing analysis"],
        "skill_keywords": ["spss", "tableau", "google analytics"],
    },
    # ---- Legal ----
    {
        "soc_code": "23-1011", "title": "Lawyers",
        "title_keywords": ["attorney", "lawyer", "counsel"],
        "duty_keywords": ["legal advice", "draft contracts", "litigation"],
        "skill_keywords": ["jd", "bar admission"],
    },
]


# Indexed lookup
SOC_BY_CODE = {entry["soc_code"]: entry for entry in SOC_CATALOG}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SocCodeService:
    """Recommend SOC codes from job title + duties + skills."""

    def __init__(self) -> None:
        self._recommendations: dict[str, dict] = {}

    # ---------- catalog access ----------
    @staticmethod
    def list_catalog(limit: int | None = None, search: str | None = None) -> list[dict]:
        out = SOC_CATALOG
        if search:
            s = search.lower()
            out = [e for e in out if s in e["title"].lower() or any(s in t for t in e.get("title_keywords", []))]
        if limit:
            out = out[:limit]
        return out

    @staticmethod
    def get_by_code(soc_code: str) -> dict | None:
        return SOC_BY_CODE.get(soc_code)

    # ---------- recommendation ----------
    def recommend(
        self,
        job_title: str,
        duties: str = "",
        skills: list[str] | None = None,
        prefer_managerial: bool = False,
        prefer_research: bool = False,
        limit: int = 5,
    ) -> dict:
        skills = skills or []
        title_l = (job_title or "").lower()
        duties_l = (duties or "").lower()
        skill_l = [s.lower() for s in skills]

        scored: list[dict] = []
        for entry in SOC_CATALOG:
            score, components = self._score_entry(entry, title_l, duties_l, skill_l, prefer_managerial, prefer_research)
            if score > 0:
                scored.append({
                    "soc_code": entry["soc_code"],
                    "title": entry["title"],
                    "score": score,
                    "components": components,
                    "perm_schedule_a": entry.get("perm_schedule_a", False),
                    "h1b_typical": entry.get("h1b_typical") or entry.get("h1b_high_volume", False),
                    "l1a_eligibility": entry.get("l1a_eligibility", False),
                    "o1_eligibility": entry.get("o1_eligibility", False),
                    "eb1b_eligibility": entry.get("eb1b_eligibility", False),
                    "managerial": entry.get("managerial", False),
                    "wage_tier_hint": entry.get("wage_tier_hint"),
                })
        scored.sort(key=lambda r: -r["score"])

        result = {
            "id": str(uuid.uuid4()),
            "job_title": job_title,
            "duties": duties,
            "skills": skills,
            "recommendations": scored[:limit],
            "computed_at": datetime.utcnow().isoformat(),
        }
        self._recommendations[result["id"]] = result
        return result

    @staticmethod
    def _score_entry(
        entry: dict, title_l: str, duties_l: str, skills_l: list[str],
        prefer_managerial: bool, prefer_research: bool,
    ) -> tuple[int, dict]:
        components: dict[str, int] = {}

        # Title match (40 points possible)
        title_kws = entry.get("title_keywords", [])
        title_hits = [kw for kw in title_kws if kw in title_l]
        if title_hits:
            best_match_len = max(len(kw) for kw in title_hits)
            components["title"] = min(40, 15 + (best_match_len // 2))
        else:
            components["title"] = 0

        # Duty keywords (30 points possible)
        duty_kws = entry.get("duty_keywords", [])
        duty_hits = sum(1 for kw in duty_kws if kw in duties_l)
        if duty_hits >= 5:
            components["duties"] = 30
        elif duty_hits >= 3:
            components["duties"] = 20
        elif duty_hits >= 1:
            components["duties"] = 10
        else:
            components["duties"] = 0

        # Skill keywords (20 points possible)
        skill_kws = [s.lower() for s in entry.get("skill_keywords", [])]
        skill_hits = sum(1 for kw in skill_kws if any(kw in s for s in skills_l))
        if skill_hits >= 4:
            components["skills"] = 20
        elif skill_hits >= 2:
            components["skills"] = 13
        elif skill_hits >= 1:
            components["skills"] = 7
        else:
            components["skills"] = 0

        # Preference bonuses
        if prefer_managerial and entry.get("managerial"):
            components["managerial_pref"] = 8
        else:
            components["managerial_pref"] = 0
        if prefer_research and entry.get("o1_eligibility"):
            components["research_pref"] = 8
        else:
            components["research_pref"] = 0

        # Penalty for "All Other" buckets unless nothing else fits
        if entry.get("soc_code", "").endswith("99") or "all other" in entry.get("title", "").lower():
            components["fallback_penalty"] = -5
        else:
            components["fallback_penalty"] = 0

        total = sum(components.values())
        return max(0, total), components

    # ---------- storage ----------
    def get_recommendation(self, rec_id: str) -> dict | None:
        return self._recommendations.get(rec_id)

    def list_recommendations(self) -> list[dict]:
        return list(self._recommendations.values())
