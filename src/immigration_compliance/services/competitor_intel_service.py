"""Competitor intelligence service — track and outperform every competitor."""

from __future__ import annotations

from datetime import datetime


class CompetitorIntelService:
    """Competitor analysis and threat assessment."""

    _COMPETITORS: dict[str, dict] = {
        "casium": {
            "name": "Casium",
            "founded": "2024",
            "funding": "$5M seed (AI2 Incubator, 2025)",
            "hq": "Seattle, WA",
            "target_market": "Immigration attorneys — mid-size firms",
            "key_features": [
                "Agentic AI for visa filings",
                "Scans public data to pre-fill forms",
                "Automated petition assembly",
                "RFE response drafting",
            ],
            "pricing": "Subscription — estimated $200-500/month per attorney",
            "differentiator": "AI2 incubator pedigree, agentic AI that autonomously assembles petitions",
            "threat_level": "high",
            "threat_reason": "Direct competitor to our agentic pipeline. Well-funded with AI research backing.",
            "verom_advantages": [
                "Full platform (marketplace + tools) vs their tools-only approach",
                "Escrow payment system they don't have",
                "Multi-country support (they focus US only)",
                "Applicant-facing portal (they're attorney-only)",
                "Government portal unification across 6+ countries",
            ],
            "counter_strategy": "Ship agentic pipeline faster with broader scope. Emphasize marketplace + tools ecosystem.",
        },
        "legalbridge_ai": {
            "name": "LegalBridge AI",
            "founded": "2024",
            "funding": "Undisclosed",
            "hq": "Unknown",
            "target_market": "Immigration law firms — 70+ firms using as of 2026",
            "key_features": [
                "AI case management",
                "60% preparation time reduction claim",
                "Document automation",
                "Case timeline tracking",
                "Client intake automation",
            ],
            "pricing": "Per-firm licensing — estimated $300-800/month",
            "differentiator": "Rapid adoption (70+ firms), ABA TECHSHOW 2026 presence",
            "threat_level": "high",
            "threat_reason": "Growing fast with attorney adoption. Similar feature set to our attorney portal.",
            "verom_advantages": [
                "Marketplace connecting attorneys with clients",
                "Escrow and payment infrastructure",
                "350+ government forms library",
                "Multi-country support",
                "Applicant self-service portal",
                "Government portal unification",
            ],
            "counter_strategy": "Match their time-saving claims with concrete metrics. Push marketplace as unique differentiator.",
        },
        "us_immigration_ai": {
            "name": "US Immigration AI",
            "founded": "2025",
            "funding": "Undisclosed",
            "hq": "Los Angeles, CA",
            "target_market": "Full-spectrum immigration practitioners",
            "key_features": [
                "Unified AI case solution",
                "Client intake",
                "Form preparation",
                "Case tracking",
                "Document management",
            ],
            "pricing": "Unknown — likely SaaS subscription",
            "differentiator": "Full-spectrum approach covering all immigration case types",
            "threat_level": "medium",
            "threat_reason": "Broad scope but early-stage. Limited traction data available.",
            "verom_advantages": [
                "More mature platform with proven features",
                "Multi-country (they appear US-only)",
                "Marketplace with escrow",
                "Attorney verification and fraud detection",
                "Applicant protection mechanisms",
            ],
            "counter_strategy": "Move fast on Tier 1 features to maintain lead. Their broad-but-shallow approach loses to our deep features.",
        },
        "deel_immigration": {
            "name": "Deel Immigration (formerly LegalPad)",
            "founded": "2019 (LegalPad), acquired by Deel 2022",
            "funding": "Backed by Deel ($679M+ raised)",
            "hq": "San Francisco, CA",
            "target_market": "Employers — bundled with Deel payroll/HR in 25+ countries",
            "key_features": [
                "Employer-sponsored visa services in 25+ countries",
                "Bundled with Deel payroll and compliance",
                "H-1B, O-1, TN, Green Card support",
                "Global mobility management",
                "Integrated with HR workflows",
            ],
            "pricing": "Bundled with Deel platform — premium add-on",
            "differentiator": "Incredibly sticky — companies using Deel payroll get immigration bundled in",
            "threat_level": "high",
            "threat_reason": "Deel has massive existing customer base. Bundling makes switching cost very high.",
            "verom_advantages": [
                "Attorney marketplace (Deel uses internal attorneys only)",
                "Applicant self-service portal",
                "AI-powered case analysis (deeper than Deel's)",
                "Community and peer network for attorneys",
                "Not locked into a single payroll vendor",
                "Transparent escrow (Deel pricing is opaque)",
            ],
            "counter_strategy": "Position as the open platform vs Deel's walled garden. Target firms not on Deel payroll. Build HRIS integrations to match their bundling advantage.",
        },
        "alma": {
            "name": "Alma",
            "founded": "2023",
            "funding": "Undisclosed",
            "hq": "Unknown",
            "target_market": "Individual applicants — O-1A and H-1B specifically",
            "key_features": [
                "O-1A visa specialization",
                "H-1B petition support",
                "Flat-rate pricing model",
                "Claims 99%+ approval rate",
                "Streamlined application process",
            ],
            "pricing": "Flat-rate — estimated $3,000-8,000 per case",
            "differentiator": "Consumer-friendly flat pricing, exceptional approval rate claims",
            "threat_level": "medium",
            "threat_reason": "Strong consumer appeal for O-1A/H-1B niche. Flat pricing is attractive.",
            "verom_advantages": [
                "Full platform vs niche service",
                "Multi-visa-type support (not just O-1A/H-1B)",
                "Multi-country support",
                "Attorney choice via marketplace (not a single-provider model)",
                "Employer compliance tools",
                "Transparent escrow vs flat rate",
            ],
            "counter_strategy": "Ensure our O-1A and H-1B workflows are equally streamlined. Compete on breadth and attorney choice.",
        },
    }

    def get_competitor(self, name: str) -> dict | None:
        return self._COMPETITORS.get(name.lower().replace(" ", "_").replace("-", "_"))

    def get_all_competitors(self) -> list[dict]:
        return list(self._COMPETITORS.values())

    def get_threat_matrix(self) -> dict:
        matrix = []
        for key, c in self._COMPETITORS.items():
            matrix.append({
                "name": c["name"],
                "threat_level": c["threat_level"],
                "target_overlap": self._calc_overlap(c),
                "feature_overlap": self._calc_feature_overlap(c),
                "funding_level": c["funding"],
                "key_risk": c["threat_reason"],
            })
        matrix.sort(key=lambda x: {"high": 0, "medium": 1, "low": 2}[x["threat_level"]])
        return {
            "assessed_at": datetime.utcnow().isoformat(),
            "total_competitors": len(matrix),
            "high_threat": len([m for m in matrix if m["threat_level"] == "high"]),
            "competitors": matrix,
        }

    def get_feature_gaps(self) -> list[dict]:
        return [
            {"feature": "Agentic AI petition assembly", "competitors": ["Casium"], "priority": "critical", "status": "building"},
            {"feature": "Bundled HR/payroll integration", "competitors": ["Deel Immigration"], "priority": "high", "status": "partial"},
            {"feature": "Flat-rate consumer pricing model", "competitors": ["Alma"], "priority": "medium", "status": "not_started"},
            {"feature": "60% prep time reduction metrics", "competitors": ["LegalBridge AI"], "priority": "high", "status": "need_benchmarks"},
        ]

    def get_advantages(self) -> list[dict]:
        return [
            {"feature": "Attorney marketplace with escrow", "unique_to_verom": True, "competitors_lacking": ["Casium", "LegalBridge AI", "US Immigration AI"]},
            {"feature": "Multi-country support (6+ countries)", "unique_to_verom": True, "competitors_lacking": ["Casium", "LegalBridge AI", "US Immigration AI", "Alma"]},
            {"feature": "Applicant self-service portal", "unique_to_verom": True, "competitors_lacking": ["Casium", "LegalBridge AI"]},
            {"feature": "Government portal unification (USCIS + DOL + EOIR + UK + CA + AU)", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
            {"feature": "350+ government forms library with auto-fill", "unique_to_verom": True, "competitors_lacking": ["Casium", "Alma", "US Immigration AI"]},
            {"feature": "Attorney verification and fraud detection", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
            {"feature": "Escrow with milestone-based payments", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
            {"feature": "ICE audit simulator", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
            {"feature": "Gamified compliance scoring", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
            {"feature": "Cross-country strategy optimizer", "unique_to_verom": True, "competitors_lacking": ["All competitors"]},
        ]

    def _calc_overlap(self, competitor: dict) -> str:
        market = competitor["target_market"].lower()
        if "attorney" in market and "employer" in market:
            return "high"
        if "attorney" in market or "employer" in market:
            return "medium"
        return "low"

    def _calc_feature_overlap(self, competitor: dict) -> str:
        features = len(competitor.get("key_features", []))
        if features >= 5:
            return "high"
        if features >= 3:
            return "medium"
        return "low"
