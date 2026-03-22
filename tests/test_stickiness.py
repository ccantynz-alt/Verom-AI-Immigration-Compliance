"""Tests for Tier 3 Stickiness features."""

import pytest
from fastapi.testclient import TestClient

from immigration_compliance.api.app import app
from immigration_compliance.services.stickiness_service import (
    AttorneyAnalyticsService,
    BenchmarkReportService,
    CommunityForumService,
    GamifiedScoringService,
    PWAService,
)
from immigration_compliance.services.competitor_intel_service import CompetitorIntelService

client = TestClient(app)


# ── Gamified Scoring ──

class TestGamifiedScoring:
    def setup_method(self):
        self.svc = GamifiedScoringService()

    def test_firm_score(self):
        result = self.svc.get_firm_score("firm-1")
        assert 0 <= result["overall_score"] <= 100
        assert "breakdown" in result
        assert result["level"] in ("Bronze", "Silver", "Gold", "Platinum")

    def test_leaderboard(self):
        lb = self.svc.get_leaderboard()
        assert len(lb) >= 5
        assert lb[0]["score"] >= lb[-1]["score"]

    def test_award_badge(self):
        result = self.svc.award_badge("firm-1", "perfect_filing_month")
        assert result["badge"]["name"] == "Perfect Filer"

    def test_invalid_badge(self):
        with pytest.raises(ValueError):
            self.svc.award_badge("firm-1", "fake_badge")

    def test_streak(self):
        result = self.svc.get_streak("firm-1")
        assert result["current_streak"] >= 0

    def test_certification(self):
        result = self.svc.get_certification_status("firm-1")
        assert "certified" in result

    def test_api_score(self):
        resp = client.get("/api/gamification/score/firm-1")
        assert resp.status_code == 200

    def test_api_leaderboard(self):
        resp = client.get("/api/gamification/leaderboard")
        assert resp.status_code == 200


# ── Attorney Analytics ──

class TestAttorneyAnalytics:
    def setup_method(self):
        self.svc = AttorneyAnalyticsService()

    def test_outcomes(self):
        result = self.svc.get_attorney_outcomes("atty-1")
        assert result["overall_approval_rate"] > 0
        assert "H-1B" in result["by_visa_type"]

    def test_rankings(self):
        ranked = self.svc.rank_attorneys("H-1B")
        assert len(ranked) >= 3
        assert ranked[0]["approval_rate"] >= ranked[-1]["approval_rate"]

    def test_trend(self):
        trend = self.svc.get_trend("atty-1")
        assert len(trend) == 12

    def test_predict(self):
        result = self.svc.predict_outcome("atty-1", {"visa_type": "H-1B"})
        assert 0 < result["predicted_approval_probability"] <= 1

    def test_specialization(self):
        result = self.svc.get_specialization_depth("atty-1")
        assert len(result["primary_specializations"]) >= 1

    def test_api_outcomes(self):
        resp = client.get("/api/attorney-analytics/atty-1/outcomes")
        assert resp.status_code == 200

    def test_api_rankings(self):
        resp = client.get("/api/attorney-analytics/rankings/H-1B")
        assert resp.status_code == 200


# ── Community Forum ──

class TestCommunityForum:
    def setup_method(self):
        self.svc = CommunityForumService()

    def test_create_post(self):
        post = self.svc.create_post("user-1", "Test Title", "Test Content", "strategy", ["H-1B"])
        assert post["title"] == "Test Title"
        assert post["category"] == "strategy"

    def test_list_posts(self):
        self.svc.create_post("user-1", "Post 1", "Content", "strategy")
        self.svc.create_post("user-1", "Post 2", "Content", "regulatory_update")
        result = self.svc.list_posts(category="strategy")
        assert all(p["category"] == "strategy" for p in result["posts"])

    def test_add_comment(self):
        post = self.svc.create_post("user-1", "Post", "Content")
        comment = self.svc.add_comment(post["id"], "user-2", "Great post!")
        assert comment["content"] == "Great post!"

    def test_comment_nonexistent(self):
        with pytest.raises(ValueError):
            self.svc.add_comment("fake-id", "user-1", "test")

    def test_vote(self):
        post = self.svc.create_post("user-1", "Post", "Content")
        result = self.svc.vote(post["id"], "user-2", 1)
        assert result["new_vote_count"] == 1

    def test_trending(self):
        trending = self.svc.get_trending()
        assert len(trending) >= 3

    def test_reputation(self):
        self.svc.create_post("user-10", "Post", "Content")
        rep = self.svc.get_user_reputation("user-10")
        assert rep["reputation_score"] > 0

    def test_api_trending(self):
        resp = client.get("/api/forum/trending")
        assert resp.status_code == 200

    def test_api_create_post(self):
        resp = client.post("/api/forum/posts", json={
            "author_id": "user-1", "title": "Test", "content": "Hello", "category": "strategy", "tags": ["H-1B"],
        })
        assert resp.status_code == 201


# ── Benchmark Reports ──

class TestBenchmarkReports:
    def setup_method(self):
        self.svc = BenchmarkReportService()

    def test_generate_report(self):
        report = self.svc.generate_report("firm-1", 2025)
        assert report["firm_id"] == "firm-1"
        assert report["year"] == 2025
        assert "executive_summary" in report
        assert "firm_metrics" in report
        assert "industry_averages" in report
        assert "percentile_rankings" in report

    def test_industry_averages(self):
        avg = self.svc.get_industry_averages(2025)
        assert avg["approval_rate"] > 0
        assert avg["firms_in_sample"] > 0

    def test_compare_to_peers(self):
        result = self.svc.compare_to_peers("firm-1")
        assert len(result["outperforming"]) >= 0

    def test_export(self):
        result = self.svc.export_report("firm-1", 2025, "json")
        assert result["format"] == "json"

    def test_api_report(self):
        resp = client.get("/api/benchmark/firm-1/2025")
        assert resp.status_code == 200

    def test_api_industry(self):
        resp = client.get("/api/benchmark/industry/2025")
        assert resp.status_code == 200


# ── PWA ──

class TestPWA:
    def setup_method(self):
        self.svc = PWAService()

    def test_manifest(self):
        m = self.svc.get_manifest()
        assert m["name"] == "Verom.ai Immigration Platform"
        assert m["display"] == "standalone"

    def test_sw_config(self):
        config = self.svc.get_service_worker_config()
        assert config["cache_strategy"] == "stale-while-revalidate"
        assert len(config["precache"]) > 0

    def test_offline_data(self):
        data = self.svc.get_offline_data("user-1")
        assert "cases" in data
        assert "deadlines" in data

    def test_sync(self):
        result = self.svc.sync_offline_changes("user-1", [{"id": "c1", "type": "note_update"}])
        assert result["synced"] == 1

    def test_sms(self):
        result = self.svc.send_sms_update("+15551234567", "Your case was approved!")
        assert result["status"] == "queued"

    def test_push(self):
        result = self.svc.get_push_subscription("user-1")
        assert "endpoint" in result

    def test_api_manifest(self):
        resp = client.get("/api/pwa/manifest")
        assert resp.status_code == 200

    def test_api_sw_config(self):
        resp = client.get("/api/pwa/sw-config")
        assert resp.status_code == 200


# ── Competitor Intel ──

class TestCompetitorIntel:
    def setup_method(self):
        self.svc = CompetitorIntelService()

    def test_get_competitor(self):
        result = self.svc.get_competitor("casium")
        assert result is not None
        assert result["name"] == "Casium"

    def test_get_all(self):
        all_c = self.svc.get_all_competitors()
        assert len(all_c) == 5

    def test_threat_matrix(self):
        matrix = self.svc.get_threat_matrix()
        assert matrix["total_competitors"] == 5
        assert matrix["high_threat"] >= 2

    def test_feature_gaps(self):
        gaps = self.svc.get_feature_gaps()
        assert len(gaps) >= 3

    def test_advantages(self):
        adv = self.svc.get_advantages()
        assert len(adv) >= 5

    def test_api_competitors(self):
        resp = client.get("/api/intel/competitors")
        assert resp.status_code == 200

    def test_api_threat_matrix(self):
        resp = client.get("/api/intel/threat-matrix")
        assert resp.status_code == 200

    def test_api_advantages(self):
        resp = client.get("/api/intel/advantages")
        assert resp.status_code == 200
