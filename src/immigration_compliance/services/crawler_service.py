"""International competitive intelligence crawler.

Automated monitoring of immigration tech competitors worldwide.
Tracks new entrants, feature changes, funding, and market signals
across US, UK, Canada, Australia, EU, and emerging markets.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from enum import Enum


class CrawlRegion(str, Enum):
    US = "us"
    UK = "uk"
    CANADA = "canada"
    AUSTRALIA = "australia"
    EU = "eu"
    GLOBAL = "global"


class SignalType(str, Enum):
    NEW_COMPETITOR = "new_competitor"
    NEW_FEATURE = "new_feature"
    FUNDING_ROUND = "funding_round"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    PRICING_CHANGE = "pricing_change"
    MARKET_ENTRY = "market_entry"
    REGULATORY_TECH = "regulatory_tech"
    HIRING_SIGNAL = "hiring_signal"
    PATENT_FILING = "patent_filing"


class ThreatResponse(str, Enum):
    BUILD_FEATURE = "build_feature"
    ENHANCE_EXISTING = "enhance_existing"
    MONITOR = "monitor"
    COUNTER_MARKETING = "counter_marketing"
    ACQUIRE_TALENT = "acquire_talent"
    PARTNER = "partner"


class CompetitiveCrawlerService:
    """International competitive intelligence engine."""

    # Crawl sources by region
    _CRAWL_SOURCES: dict[str, list[dict]] = {
        "us": [
            {"name": "Product Hunt", "url": "producthunt.com", "type": "launch_platform", "frequency_hours": 24},
            {"name": "TechCrunch", "url": "techcrunch.com", "type": "news", "frequency_hours": 12},
            {"name": "Crunchbase", "url": "crunchbase.com", "type": "funding", "frequency_hours": 24},
            {"name": "AILA TechConnect", "url": "aila.org", "type": "industry", "frequency_hours": 168},
            {"name": "ABA Legal Tech", "url": "americanbar.org", "type": "industry", "frequency_hours": 168},
            {"name": "GitHub Trending", "url": "github.com/trending", "type": "open_source", "frequency_hours": 24},
            {"name": "AngelList", "url": "angel.co", "type": "startups", "frequency_hours": 48},
            {"name": "LinkedIn Jobs", "url": "linkedin.com/jobs", "type": "hiring", "frequency_hours": 48},
            {"name": "USPTO Patent Search", "url": "patft.uspto.gov", "type": "patents", "frequency_hours": 168},
        ],
        "uk": [
            {"name": "LegalTech UK", "url": "legaltechnology.com", "type": "industry", "frequency_hours": 168},
            {"name": "TechNation", "url": "technation.io", "type": "startups", "frequency_hours": 48},
            {"name": "SRA Register", "url": "sra.org.uk", "type": "regulatory", "frequency_hours": 168},
            {"name": "Law Society Gazette", "url": "lawgazette.co.uk", "type": "industry", "frequency_hours": 48},
        ],
        "canada": [
            {"name": "BetaKit", "url": "betakit.com", "type": "news", "frequency_hours": 24},
            {"name": "MaRS Discovery", "url": "marsdd.com", "type": "startups", "frequency_hours": 48},
            {"name": "CBA Legal Tech", "url": "cba.org", "type": "industry", "frequency_hours": 168},
        ],
        "australia": [
            {"name": "SmartCompany", "url": "smartcompany.com.au", "type": "news", "frequency_hours": 48},
            {"name": "LegalTech AU", "url": "lawtechnologist.com.au", "type": "industry", "frequency_hours": 168},
            {"name": "MARA Register", "url": "mara.gov.au", "type": "regulatory", "frequency_hours": 168},
        ],
        "eu": [
            {"name": "EU-Startups", "url": "eu-startups.com", "type": "startups", "frequency_hours": 48},
            {"name": "Sifted", "url": "sifted.eu", "type": "news", "frequency_hours": 24},
            {"name": "LegalTech Hub EU", "url": "legaltechhub.eu", "type": "industry", "frequency_hours": 168},
        ],
    }

    # Keywords to crawl for across all sources
    _CRAWL_KEYWORDS: list[str] = [
        "immigration software", "immigration tech", "immigration platform",
        "visa management", "visa automation", "visa filing",
        "immigration AI", "immigration compliance", "immigration SaaS",
        "H-1B software", "work permit automation", "global mobility platform",
        "immigration case management", "legal immigration tech",
        "e-verify software", "I-9 automation", "immigration analytics",
        "attorney immigration tools", "immigration marketplace",
        "immigration workflow", "petition automation",
    ]

    def __init__(self) -> None:
        self._signals: list[dict] = []
        self._crawl_log: list[dict] = []
        self._watchlist: list[dict] = []
        self._threat_responses: list[dict] = []
        self._seed_signals()

    def _seed_signals(self) -> None:
        """Pre-seed with known competitive intelligence signals."""
        known_signals = [
            {
                "type": SignalType.NEW_COMPETITOR.value,
                "region": CrawlRegion.US.value,
                "entity": "Casium",
                "headline": "Casium raises $5M seed from AI2 Incubator for agentic immigration AI",
                "detail": "Seattle-based startup building autonomous visa petition assembly. AI2 pedigree suggests strong technical team.",
                "source": "Crunchbase / TechCrunch",
                "threat_level": "high",
                "detected_at": "2025-09-15T00:00:00",
                "response_status": "countered",
                "response_action": "Built agentic pipeline + marketplace + multi-country (they're attorney-only, US-only)",
            },
            {
                "type": SignalType.NEW_FEATURE.value,
                "region": CrawlRegion.US.value,
                "entity": "LegalBridge AI",
                "headline": "LegalBridge AI claims 60% case prep time reduction at ABA TECHSHOW 2026",
                "detail": "Now in 70+ firms. No public methodology for their time-savings claims.",
                "source": "ABA TECHSHOW 2026",
                "threat_level": "high",
                "detected_at": "2026-02-20T00:00:00",
                "response_status": "countered",
                "response_action": "Built benchmarking engine with >79% reduction and transparent methodology with cited data sources",
            },
            {
                "type": SignalType.ACQUISITION.value,
                "region": CrawlRegion.US.value,
                "entity": "Deel Immigration",
                "headline": "Deel acquired LegalPad, now offers immigration in 25+ countries bundled with payroll",
                "detail": "Incredibly sticky — employers using Deel payroll get immigration bundled. $679M+ total funding.",
                "source": "Crunchbase",
                "threat_level": "high",
                "detected_at": "2022-06-01T00:00:00",
                "response_status": "countered",
                "response_action": "Built deep HRIS integration with lifecycle events, payroll alerts, and Deel import tool",
            },
            {
                "type": SignalType.PRICING_CHANGE.value,
                "region": CrawlRegion.US.value,
                "entity": "Alma",
                "headline": "Alma offering flat-rate O-1A/H-1B pricing with 99%+ claimed approval rate",
                "detail": "Consumer-friendly pricing model. Niche focus on O-1A and H-1B only.",
                "source": "Product Hunt / Direct",
                "threat_level": "medium",
                "detected_at": "2025-11-01T00:00:00",
                "response_status": "countered",
                "response_action": "Built flat-rate pricing service with 6 package templates + milestone escrow",
            },
            {
                "type": SignalType.NEW_COMPETITOR.value,
                "region": CrawlRegion.US.value,
                "entity": "US Immigration AI",
                "headline": "US Immigration AI launches full-spectrum AI case management from Los Angeles",
                "detail": "Broad scope but early stage. Limited traction data. US-only.",
                "source": "LinkedIn / Direct",
                "threat_level": "medium",
                "detected_at": "2025-06-01T00:00:00",
                "response_status": "countered",
                "response_action": "Multi-country support + marketplace + deeper features across all tiers",
            },
            {
                "type": SignalType.REGULATORY_TECH.value,
                "region": CrawlRegion.US.value,
                "entity": "USCIS",
                "headline": "USCIS deploys PAiTH AI for same-day RFE issuance",
                "detail": "Government using AI to analyze petitions means higher RFE rates for poorly prepared filings.",
                "source": "Federal Register / USCIS",
                "threat_level": "medium",
                "detected_at": "2025-12-01T00:00:00",
                "response_status": "countered",
                "response_action": "Built pre-filing compliance scanner that mirrors PAiTH analysis to catch issues before filing",
            },
            {
                "type": SignalType.REGULATORY_TECH.value,
                "region": CrawlRegion.US.value,
                "entity": "USCIS",
                "headline": "H-1B wage-weighted lottery takes effect for FY2027",
                "detail": "Higher wage levels get higher selection probability. Major impact on employer strategy.",
                "source": "Federal Register",
                "threat_level": "low",
                "detected_at": "2026-03-01T00:00:00",
                "response_status": "countered",
                "response_action": "Built H-1B wage-weighted lottery simulator with cost-benefit analysis",
            },
            {
                "type": SignalType.NEW_FEATURE.value,
                "region": CrawlRegion.UK.value,
                "entity": "Jobbatical",
                "headline": "Jobbatical expands to UK market with employer global mobility tools",
                "detail": "Estonian company now offering UK Skilled Worker visa management for employers.",
                "source": "EU-Startups",
                "threat_level": "low",
                "detected_at": "2026-01-15T00:00:00",
                "response_status": "monitoring",
                "response_action": "Already have UK support. Monitor for feature differentiation.",
            },
            {
                "type": SignalType.FUNDING_ROUND.value,
                "region": CrawlRegion.EU.value,
                "entity": "Localyze",
                "headline": "Localyze (Berlin) raises Series B for global mobility platform",
                "detail": "EU-focused global mobility and immigration. Strong in Germany, expanding to UK.",
                "source": "Sifted",
                "threat_level": "low",
                "detected_at": "2025-10-01T00:00:00",
                "response_status": "monitoring",
                "response_action": "Already cover Germany. Monitor EU expansion.",
            },
            {
                "type": SignalType.HIRING_SIGNAL.value,
                "region": CrawlRegion.US.value,
                "entity": "Fragomen",
                "headline": "Fragomen posting multiple AI/ML engineering roles",
                "detail": "Traditional firm investing in AI capabilities. Hiring indicates product development push.",
                "source": "LinkedIn Jobs",
                "threat_level": "medium",
                "detected_at": "2026-02-01T00:00:00",
                "response_status": "monitoring",
                "response_action": "Our AI capabilities are 2+ years ahead. Continue building moat.",
            },
        ]
        for s in known_signals:
            s["id"] = str(uuid.uuid4())
        self._signals = known_signals

    # -----------------------------------------------------------------------
    # Crawl management
    # -----------------------------------------------------------------------

    def get_crawl_sources(self, region: str | None = None) -> dict:
        """Get all configured crawl sources by region."""
        if region:
            sources = self._CRAWL_SOURCES.get(region, [])
            return {"region": region, "sources": sources, "total": len(sources)}
        total = sum(len(s) for s in self._CRAWL_SOURCES.values())
        return {
            "regions": {k: len(v) for k, v in self._CRAWL_SOURCES.items()},
            "total_sources": total,
            "sources_by_region": self._CRAWL_SOURCES,
            "crawl_keywords": self._CRAWL_KEYWORDS,
        }

    def get_crawl_keywords(self) -> list[str]:
        return self._CRAWL_KEYWORDS

    def add_crawl_keyword(self, keyword: str) -> list[str]:
        if keyword not in self._CRAWL_KEYWORDS:
            self._CRAWL_KEYWORDS.append(keyword)
        return self._CRAWL_KEYWORDS

    def run_crawl(self, region: str = "global") -> dict:
        """Execute a crawl cycle (simulated — in production uses scheduled HTTP fetches)."""
        sources = []
        if region == "global":
            for r_sources in self._CRAWL_SOURCES.values():
                sources.extend(r_sources)
        else:
            sources = self._CRAWL_SOURCES.get(region, [])

        crawl_id = str(uuid.uuid4())
        crawl_record = {
            "id": crawl_id,
            "region": region,
            "sources_checked": len(sources),
            "keywords_searched": len(self._CRAWL_KEYWORDS),
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "new_signals_found": 0,
            "status": "completed",
        }
        self._crawl_log.append(crawl_record)
        return crawl_record

    def get_crawl_log(self, limit: int = 20) -> list[dict]:
        return self._crawl_log[-limit:]

    # -----------------------------------------------------------------------
    # Signal management
    # -----------------------------------------------------------------------

    def get_signals(
        self,
        region: str | None = None,
        signal_type: str | None = None,
        threat_level: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get competitive intelligence signals with filtering."""
        signals = self._signals
        if region:
            signals = [s for s in signals if s["region"] == region]
        if signal_type:
            signals = [s for s in signals if s["type"] == signal_type]
        if threat_level:
            signals = [s for s in signals if s["threat_level"] == threat_level]
        if status:
            signals = [s for s in signals if s["response_status"] == status]
        return signals[:limit]

    def add_signal(self, signal_data: dict) -> dict:
        """Manually add a competitive intelligence signal."""
        signal = {
            "id": str(uuid.uuid4()),
            "type": signal_data.get("type", SignalType.NEW_COMPETITOR.value),
            "region": signal_data.get("region", CrawlRegion.US.value),
            "entity": signal_data.get("entity", ""),
            "headline": signal_data.get("headline", ""),
            "detail": signal_data.get("detail", ""),
            "source": signal_data.get("source", ""),
            "threat_level": signal_data.get("threat_level", "medium"),
            "detected_at": datetime.utcnow().isoformat(),
            "response_status": "new",
            "response_action": "",
        }
        self._signals.append(signal)
        return signal

    def update_signal_response(self, signal_id: str, status: str, action: str) -> dict | None:
        """Update the response status and action for a signal."""
        for s in self._signals:
            if s["id"] == signal_id:
                s["response_status"] = status
                s["response_action"] = action
                return s
        return None

    # -----------------------------------------------------------------------
    # Threat dashboard
    # -----------------------------------------------------------------------

    def get_threat_dashboard(self) -> dict:
        """Comprehensive competitive threat overview."""
        signals = self._signals
        by_level = {"high": 0, "medium": 0, "low": 0}
        by_status = {"countered": 0, "monitoring": 0, "new": 0, "in_progress": 0}
        by_region = {}
        by_type = {}

        for s in signals:
            by_level[s.get("threat_level", "low")] = by_level.get(s.get("threat_level", "low"), 0) + 1
            by_status[s.get("response_status", "new")] = by_status.get(s.get("response_status", "new"), 0) + 1
            r = s.get("region", "unknown")
            by_region[r] = by_region.get(r, 0) + 1
            t = s.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        uncountered_high = [s for s in signals if s["threat_level"] == "high" and s["response_status"] != "countered"]

        return {
            "dashboard_date": datetime.utcnow().isoformat(),
            "total_signals": len(signals),
            "by_threat_level": by_level,
            "by_response_status": by_status,
            "by_region": by_region,
            "by_signal_type": by_type,
            "uncountered_high_threats": uncountered_high,
            "competitive_position": "strong" if not uncountered_high else "at_risk",
            "crawl_sources_configured": sum(len(v) for v in self._CRAWL_SOURCES.values()),
            "regions_monitored": len(self._CRAWL_SOURCES),
            "keywords_tracked": len(self._CRAWL_KEYWORDS),
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> list[dict]:
        """AI-generated recommendations based on current signal landscape."""
        recs = []
        uncountered = [s for s in self._signals if s["response_status"] not in ("countered",)]
        if uncountered:
            recs.append({
                "priority": "high",
                "action": f"Address {len(uncountered)} signals still being monitored or new",
                "detail": "Review monitoring signals for potential threats that need active counter-features",
            })

        high_threats = [s for s in self._signals if s["threat_level"] == "high"]
        if len(high_threats) >= 3:
            recs.append({
                "priority": "high",
                "action": "Multiple high-threat competitors — accelerate differentiation",
                "detail": "Focus on unique features no competitor has: escrow, government portal unification, multi-country",
            })

        recs.append({
            "priority": "medium",
            "action": "Expand crawl coverage to Asia-Pacific markets",
            "detail": "Japan, Singapore, South Korea emerging immigration tech markets not yet monitored",
        })

        recs.append({
            "priority": "medium",
            "action": "Monitor for AI regulation impact on immigration tech",
            "detail": "EU AI Act and US executive orders may affect AI-powered immigration tools",
        })

        return recs

    # -----------------------------------------------------------------------
    # Watchlist management
    # -----------------------------------------------------------------------

    def add_to_watchlist(self, entity_data: dict) -> dict:
        """Add a company or product to the active monitoring watchlist."""
        entry = {
            "id": str(uuid.uuid4()),
            "entity": entity_data.get("entity", ""),
            "type": entity_data.get("type", "company"),
            "url": entity_data.get("url", ""),
            "region": entity_data.get("region", "us"),
            "check_frequency_hours": entity_data.get("frequency_hours", 48),
            "keywords": entity_data.get("keywords", []),
            "last_checked": None,
            "added_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self._watchlist.append(entry)
        return entry

    def get_watchlist(self) -> list[dict]:
        return self._watchlist

    def remove_from_watchlist(self, entity_id: str) -> bool:
        self._watchlist = [w for w in self._watchlist if w["id"] != entity_id]
        return True

    # -----------------------------------------------------------------------
    # Competitive gap analysis
    # -----------------------------------------------------------------------

    def get_feature_landscape(self) -> dict:
        """Map of who has what across the competitive landscape."""
        features = {
            "AI document processing": {"verom": True, "casium": True, "legalbridge": True, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Agentic AI pipeline": {"verom": True, "casium": True, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Attorney marketplace": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Escrow payments": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Multi-country (6+)": {"verom": True, "casium": False, "legalbridge": False, "deel": True, "alma": False, "fragomen": True, "envoy": True},
            "Flat-rate pricing": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": True, "fragomen": False, "envoy": False},
            "HRIS integration": {"verom": True, "casium": False, "legalbridge": False, "deel": True, "alma": False, "fragomen": True, "envoy": True},
            "Government portal unification": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Pre-filing AI scanner": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "H-1B lottery simulator": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "EAD gap manager": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Applicant self-service": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": True, "fragomen": False, "envoy": False},
            "Employer compliance dashboard": {"verom": True, "casium": False, "legalbridge": False, "deel": True, "alma": False, "fragomen": True, "envoy": True},
            "ICE audit simulator": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Attorney verification": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Gamified compliance": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Community forum": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Time-savings benchmarks": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Social media audit": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
            "Compensation planner": {"verom": True, "casium": False, "legalbridge": False, "deel": False, "alma": False, "fragomen": False, "envoy": False},
        }

        # Calculate scores
        scores = {}
        for company in ["verom", "casium", "legalbridge", "deel", "alma", "fragomen", "envoy"]:
            scores[company] = sum(1 for f in features.values() if f.get(company, False))

        verom_score = scores.pop("verom")
        max_competitor = max(scores.values()) if scores else 0
        lead_percentage = round(((verom_score - max_competitor) / max_competitor * 100), 0) if max_competitor else 100

        return {
            "features_tracked": len(features),
            "feature_matrix": features,
            "scores": {"verom": verom_score, **scores},
            "verom_lead_percentage": lead_percentage,
            "verom_unique_features": sum(
                1 for f in features.values()
                if f.get("verom") and not any(f.get(c) for c in ["casium", "legalbridge", "deel", "alma", "fragomen", "envoy"])
            ),
            "assessment": f"Verom leads with {verom_score}/{len(features)} features ({lead_percentage}% ahead of closest competitor)",
        }
