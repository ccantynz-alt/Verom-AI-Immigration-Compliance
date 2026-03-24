"""Tests for competitive intelligence crawler service."""

from immigration_compliance.services.crawler_service import (
    CompetitiveCrawlerService,
    CrawlRegion,
    SignalType,
)


class TestCompetitiveCrawler:

    def setup_method(self):
        self.svc = CompetitiveCrawlerService()

    def test_get_all_crawl_sources(self):
        result = self.svc.get_crawl_sources()
        assert result["total_sources"] >= 20
        assert "us" in result["regions"]
        assert "uk" in result["regions"]
        assert "eu" in result["regions"]

    def test_get_crawl_sources_by_region(self):
        result = self.svc.get_crawl_sources("us")
        assert result["region"] == "us"
        assert result["total"] >= 8

    def test_crawl_keywords_comprehensive(self):
        keywords = self.svc.get_crawl_keywords()
        assert len(keywords) >= 15
        assert "immigration AI" in keywords
        assert "visa management" in keywords

    def test_add_crawl_keyword(self):
        original = len(self.svc.get_crawl_keywords())
        self.svc.add_crawl_keyword("new immigration tool")
        assert len(self.svc.get_crawl_keywords()) == original + 1

    def test_add_duplicate_keyword_ignored(self):
        original = len(self.svc.get_crawl_keywords())
        self.svc.add_crawl_keyword("immigration AI")
        assert len(self.svc.get_crawl_keywords()) == original

    def test_run_crawl(self):
        result = self.svc.run_crawl("us")
        assert result["status"] == "completed"
        assert result["sources_checked"] >= 8

    def test_run_global_crawl(self):
        result = self.svc.run_crawl("global")
        assert result["sources_checked"] >= 20

    def test_crawl_log(self):
        self.svc.run_crawl("us")
        self.svc.run_crawl("uk")
        log = self.svc.get_crawl_log()
        assert len(log) == 2

    def test_seeded_signals_exist(self):
        signals = self.svc.get_signals()
        assert len(signals) >= 8

    def test_filter_signals_by_threat_level(self):
        high = self.svc.get_signals(threat_level="high")
        assert len(high) >= 3
        assert all(s["threat_level"] == "high" for s in high)

    def test_filter_signals_by_region(self):
        us = self.svc.get_signals(region="us")
        assert len(us) >= 5

    def test_filter_signals_by_type(self):
        new_comp = self.svc.get_signals(signal_type="new_competitor")
        assert len(new_comp) >= 2

    def test_add_signal(self):
        signal = self.svc.add_signal({
            "type": "new_competitor",
            "region": "uk",
            "entity": "TestCorp",
            "headline": "TestCorp launches immigration AI in UK",
            "threat_level": "medium",
        })
        assert signal["entity"] == "TestCorp"
        assert signal["response_status"] == "new"

    def test_update_signal_response(self):
        signals = self.svc.get_signals()
        signal_id = signals[0]["id"]
        updated = self.svc.update_signal_response(signal_id, "countered", "Built feature X")
        assert updated["response_status"] == "countered"

    def test_threat_dashboard(self):
        dashboard = self.svc.get_threat_dashboard()
        assert dashboard["total_signals"] >= 8
        assert "by_threat_level" in dashboard
        assert "by_response_status" in dashboard
        assert "by_region" in dashboard
        assert "recommendations" in dashboard
        assert dashboard["crawl_sources_configured"] >= 20

    def test_threat_dashboard_competitive_position(self):
        dashboard = self.svc.get_threat_dashboard()
        # All high threats should be countered based on seed data
        assert dashboard["competitive_position"] in ("strong", "at_risk")

    def test_watchlist_operations(self):
        entry = self.svc.add_to_watchlist({
            "entity": "NewStartup",
            "url": "newstartup.com",
            "region": "us",
        })
        assert entry["status"] == "active"
        watchlist = self.svc.get_watchlist()
        assert len(watchlist) == 1
        self.svc.remove_from_watchlist(entry["id"])
        assert len(self.svc.get_watchlist()) == 0

    def test_feature_landscape(self):
        landscape = self.svc.get_feature_landscape()
        assert landscape["features_tracked"] >= 18
        assert landscape["scores"]["verom"] >= 18
        assert landscape["verom_lead_percentage"] > 50
        assert landscape["verom_unique_features"] >= 10

    def test_verom_leads_all_competitors(self):
        landscape = self.svc.get_feature_landscape()
        verom_score = landscape["scores"]["verom"]
        for company, score in landscape["scores"].items():
            if company != "verom":
                assert verom_score > score, f"Verom ({verom_score}) should beat {company} ({score})"

    def test_recommendations_generated(self):
        dashboard = self.svc.get_threat_dashboard()
        recs = dashboard["recommendations"]
        assert len(recs) >= 2
        assert all("priority" in r and "action" in r for r in recs)
