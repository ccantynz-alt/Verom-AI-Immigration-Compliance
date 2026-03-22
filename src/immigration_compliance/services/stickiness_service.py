"""Tier 3 Stickiness features — users never leave."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta


# ---------------------------------------------------------------------------
# 1. Gamified Compliance Scoring
# ---------------------------------------------------------------------------

class GamifiedScoringService:
    """Firm-wide compliance scoring with badges, streaks, and leaderboards."""

    _BADGES = {
        "perfect_filing_month": {"name": "Perfect Filer", "description": "Zero filing errors for a full month", "icon": "star"},
        "zero_rfe_quarter": {"name": "RFE-Free Quarter", "description": "No RFEs received in a full quarter", "icon": "shield"},
        "100pct_on_time": {"name": "Always On Time", "description": "100% of deadlines met for 90 days", "icon": "clock"},
        "client_champion": {"name": "Client Champion", "description": "Average client rating above 4.8", "icon": "heart"},
        "compliance_master": {"name": "Compliance Master", "description": "Sustained 95+ compliance score for 6 months", "icon": "trophy"},
    }

    def __init__(self) -> None:
        self._scores: dict[str, dict] = {}
        self._badges: dict[str, list[str]] = {}
        self._streaks: dict[str, int] = {}

    def get_firm_score(self, firm_id: str) -> dict:
        return {
            "firm_id": firm_id,
            "overall_score": 87,
            "level": "Gold",
            "breakdown": {
                "filing_timeliness": 92,
                "document_completeness": 85,
                "deadline_adherence": 90,
                "response_time": 88,
                "client_satisfaction": 82,
            },
            "badges": list(self._badges.get(firm_id, ["perfect_filing_month", "100pct_on_time"])),
            "badge_details": [self._BADGES[b] for b in self._badges.get(firm_id, ["perfect_filing_month", "100pct_on_time"])],
            "current_streak": self._streaks.get(firm_id, 14),
            "streak_type": "consecutive_compliant_days",
            "next_level": "Platinum",
            "next_level_requirements": {"overall_score": 93, "min_streak": 30, "badges_needed": 4},
        }

    def get_leaderboard(self, category: str = "overall") -> list[dict]:
        return [
            {"rank": 1, "firm_id": "anon-001", "score": 96, "level": "Platinum", "badge_count": 5},
            {"rank": 2, "firm_id": "anon-002", "score": 94, "level": "Platinum", "badge_count": 4},
            {"rank": 3, "firm_id": "anon-003", "score": 91, "level": "Gold", "badge_count": 4},
            {"rank": 4, "firm_id": "anon-004", "score": 89, "level": "Gold", "badge_count": 3},
            {"rank": 5, "firm_id": "anon-005", "score": 87, "level": "Gold", "badge_count": 3},
        ]

    def award_badge(self, firm_id: str, badge_type: str) -> dict:
        if badge_type not in self._BADGES:
            raise ValueError(f"Unknown badge: {badge_type}")
        self._badges.setdefault(firm_id, []).append(badge_type)
        return {"firm_id": firm_id, "badge": self._BADGES[badge_type], "awarded_at": datetime.utcnow().isoformat()}

    def get_streak(self, firm_id: str) -> dict:
        streak = self._streaks.get(firm_id, 14)
        return {"firm_id": firm_id, "current_streak": streak, "type": "compliant_days", "best_streak": max(streak, 30)}

    def get_certification_status(self, firm_id: str) -> dict:
        score = 87
        return {
            "firm_id": firm_id,
            "certified": score >= 90,
            "certification_level": "Verom Gold" if score >= 85 else "Not Certified",
            "requirements_met": {"min_score_90": score >= 90, "min_6_months_active": True, "min_3_badges": True},
            "next_review": (date.today() + timedelta(days=90)).isoformat(),
        }


# ---------------------------------------------------------------------------
# 2. Attorney Outcome Analytics
# ---------------------------------------------------------------------------

class AttorneyAnalyticsService:
    """Match attorneys based on historical approval rates and outcomes."""

    def get_attorney_outcomes(self, attorney_id: str) -> dict:
        return {
            "attorney_id": attorney_id,
            "overall_approval_rate": 0.94,
            "by_visa_type": {
                "H-1B": {"approval_rate": 0.92, "cases": 145, "avg_processing_days": 98, "rfe_rate": 0.18},
                "O-1": {"approval_rate": 0.88, "cases": 52, "avg_processing_days": 75, "rfe_rate": 0.25},
                "L-1": {"approval_rate": 0.96, "cases": 38, "avg_processing_days": 85, "rfe_rate": 0.12},
                "I-485": {"approval_rate": 0.97, "cases": 67, "avg_processing_days": 420, "rfe_rate": 0.10},
                "EB-2 NIW": {"approval_rate": 0.85, "cases": 23, "avg_processing_days": 340, "rfe_rate": 0.30},
            },
            "rfe_response_success_rate": 0.91,
            "average_processing_time_days": 142,
            "denial_rate": 0.06,
            "platform_average_approval": 0.89,
            "above_average": True,
            "cases_completed_total": 325,
        }

    def rank_attorneys(self, visa_type: str, country: str = "US") -> list[dict]:
        return [
            {"rank": 1, "attorney_id": "atty-001", "name": "Jennifer Park", "approval_rate": 0.97, "cases": 145, "avg_days": 88, "rating": 4.9},
            {"rank": 2, "attorney_id": "atty-003", "name": "David Kim", "approval_rate": 0.96, "cases": 198, "avg_days": 92, "rating": 4.8},
            {"rank": 3, "attorney_id": "atty-002", "name": "Michael Torres", "approval_rate": 0.94, "cases": 87, "avg_days": 105, "rating": 4.7},
            {"rank": 4, "attorney_id": "atty-004", "name": "Sarah Chen", "approval_rate": 0.93, "cases": 112, "avg_days": 98, "rating": 4.8},
            {"rank": 5, "attorney_id": "atty-005", "name": "Robert Patel", "approval_rate": 0.91, "cases": 76, "avg_days": 110, "rating": 4.6},
        ]

    def get_trend(self, attorney_id: str) -> list[dict]:
        return [
            {"month": "2025-04", "approval_rate": 0.90, "cases_closed": 8, "rfe_rate": 0.22},
            {"month": "2025-05", "approval_rate": 0.91, "cases_closed": 11, "rfe_rate": 0.20},
            {"month": "2025-06", "approval_rate": 0.88, "cases_closed": 9, "rfe_rate": 0.25},
            {"month": "2025-07", "approval_rate": 0.93, "cases_closed": 12, "rfe_rate": 0.18},
            {"month": "2025-08", "approval_rate": 0.92, "cases_closed": 10, "rfe_rate": 0.19},
            {"month": "2025-09", "approval_rate": 0.94, "cases_closed": 14, "rfe_rate": 0.15},
            {"month": "2025-10", "approval_rate": 0.95, "cases_closed": 13, "rfe_rate": 0.14},
            {"month": "2025-11", "approval_rate": 0.93, "cases_closed": 11, "rfe_rate": 0.16},
            {"month": "2025-12", "approval_rate": 0.96, "cases_closed": 15, "rfe_rate": 0.12},
            {"month": "2026-01", "approval_rate": 0.94, "cases_closed": 12, "rfe_rate": 0.15},
            {"month": "2026-02", "approval_rate": 0.95, "cases_closed": 14, "rfe_rate": 0.13},
            {"month": "2026-03", "approval_rate": 0.94, "cases_closed": 10, "rfe_rate": 0.14},
        ]

    def predict_outcome(self, attorney_id: str, case_data: dict) -> dict:
        visa_type = case_data.get("visa_type", "H-1B")
        outcomes = self.get_attorney_outcomes(attorney_id)
        type_data = outcomes["by_visa_type"].get(visa_type, {})
        base_rate = type_data.get("approval_rate", 0.89)
        return {
            "attorney_id": attorney_id,
            "visa_type": visa_type,
            "predicted_approval_probability": base_rate,
            "predicted_rfe_probability": type_data.get("rfe_rate", 0.20),
            "confidence": 0.85,
            "based_on_cases": type_data.get("cases", 0),
            "factors": ["Attorney's historical success rate", "Visa type complexity", "Case completeness"],
        }

    def get_specialization_depth(self, attorney_id: str) -> dict:
        return {
            "attorney_id": attorney_id,
            "primary_specializations": [
                {"visa_type": "H-1B", "depth": "expert", "cases": 145, "years_active": 8},
                {"visa_type": "I-485", "depth": "expert", "cases": 67, "years_active": 6},
            ],
            "secondary_specializations": [
                {"visa_type": "O-1", "depth": "advanced", "cases": 52, "years_active": 5},
                {"visa_type": "L-1", "depth": "advanced", "cases": 38, "years_active": 4},
            ],
            "emerging": [
                {"visa_type": "EB-2 NIW", "depth": "developing", "cases": 23, "years_active": 2},
            ],
        }


# ---------------------------------------------------------------------------
# 3. Community Forum & Peer Network
# ---------------------------------------------------------------------------

class CommunityForumService:
    """Attorney case strategy discussions and regulatory updates."""

    def __init__(self) -> None:
        self._posts: dict[str, dict] = {}
        self._votes: dict[str, dict[str, int]] = {}  # post_id -> {user_id: direction}
        self._reputation: dict[str, int] = {}

    def create_post(self, author_id: str, title: str, content: str, category: str = "strategy", tags: list[str] | None = None) -> dict:
        post_id = str(uuid.uuid4())
        post = {
            "id": post_id,
            "author_id": author_id,
            "title": title,
            "content": content,
            "category": category,
            "tags": tags or [],
            "comments": [],
            "vote_count": 0,
            "view_count": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._posts[post_id] = post
        self._reputation[author_id] = self._reputation.get(author_id, 0) + 5
        return post

    def list_posts(self, category: str | None = None, tags: list[str] | None = None, page: int = 1, per_page: int = 20) -> dict:
        posts = list(self._posts.values())
        if category:
            posts = [p for p in posts if p["category"] == category]
        if tags:
            tag_set = set(tags)
            posts = [p for p in posts if set(p.get("tags", [])) & tag_set]
        posts.sort(key=lambda p: p["created_at"], reverse=True)
        start = (page - 1) * per_page
        return {"posts": posts[start:start + per_page], "total": len(posts), "page": page, "per_page": per_page}

    def add_comment(self, post_id: str, author_id: str, content: str) -> dict:
        post = self._posts.get(post_id)
        if not post:
            raise ValueError("Post not found")
        comment = {"id": str(uuid.uuid4()), "author_id": author_id, "content": content, "created_at": datetime.utcnow().isoformat(), "vote_count": 0}
        post["comments"].append(comment)
        post["updated_at"] = datetime.utcnow().isoformat()
        self._reputation[author_id] = self._reputation.get(author_id, 0) + 2
        return comment

    def vote(self, post_id: str, user_id: str, direction: int) -> dict:
        post = self._posts.get(post_id)
        if not post:
            raise ValueError("Post not found")
        old = self._votes.get(post_id, {}).get(user_id, 0)
        self._votes.setdefault(post_id, {})[user_id] = direction
        post["vote_count"] += direction - old
        self._reputation[post["author_id"]] = self._reputation.get(post["author_id"], 0) + direction
        return {"post_id": post_id, "new_vote_count": post["vote_count"]}

    def get_trending(self) -> list[dict]:
        return [
            {"title": "H-1B Wage-Weighted Lottery: Strategies for Level 1-2 Candidates", "category": "strategy", "vote_count": 45, "comment_count": 23, "tags": ["H-1B", "lottery"]},
            {"title": "EAD Auto-Extension Elimination — What It Means for Your Clients", "category": "regulatory_update", "vote_count": 38, "comment_count": 19, "tags": ["EAD", "policy_change"]},
            {"title": "DS-160 Social Media Disclosure Best Practices", "category": "strategy", "vote_count": 32, "comment_count": 15, "tags": ["DS-160", "compliance"]},
            {"title": "Successfully Overcoming Specialty Occupation RFEs in 2026", "category": "case_study", "vote_count": 28, "comment_count": 12, "tags": ["H-1B", "RFE"]},
            {"title": "USCIS Fee Schedule Changes — April 2026 Impact Analysis", "category": "regulatory_update", "vote_count": 25, "comment_count": 18, "tags": ["fees", "USCIS"]},
        ]

    def search_posts(self, query: str) -> list[dict]:
        query_lower = query.lower()
        results = [p for p in self._posts.values() if query_lower in p["title"].lower() or query_lower in p["content"].lower()]
        return results

    def get_user_reputation(self, user_id: str) -> dict:
        score = self._reputation.get(user_id, 0)
        level = "Expert" if score >= 100 else "Contributor" if score >= 30 else "Member"
        return {"user_id": user_id, "reputation_score": score, "level": level, "posts_count": len([p for p in self._posts.values() if p["author_id"] == user_id])}


# ---------------------------------------------------------------------------
# 4. Annual Immigration Benchmark Report
# ---------------------------------------------------------------------------

class BenchmarkReportService:
    """'Your firm vs. industry averages' — annual benchmark report."""

    def generate_report(self, firm_id: str, year: int = 2025) -> dict:
        firm = self._get_firm_metrics(firm_id, year)
        industry = self.get_industry_averages(year)
        return {
            "id": str(uuid.uuid4()),
            "firm_id": firm_id,
            "year": year,
            "executive_summary": f"In {year}, your firm filed {firm['filing_volume']} cases with a {firm['approval_rate']*100:.0f}% approval rate, outperforming the industry average of {industry['approval_rate']*100:.0f}%.",
            "firm_metrics": firm,
            "industry_averages": industry,
            "percentile_rankings": {
                "approval_rate": 82,
                "processing_time": 71,
                "filing_volume": 65,
                "rfe_rate": 78,
                "client_satisfaction": 88,
            },
            "year_over_year_change": {
                "approval_rate": +0.03,
                "filing_volume": +15,
                "avg_processing_days": -12,
                "rfe_rate": -0.04,
            },
            "visa_type_breakdown": {
                "H-1B": {"filed": 85, "approved": 78, "rfe": 15, "denied": 7},
                "L-1": {"filed": 22, "approved": 20, "rfe": 4, "denied": 2},
                "O-1": {"filed": 18, "approved": 15, "rfe": 5, "denied": 3},
                "I-485": {"filed": 35, "approved": 33, "rfe": 4, "denied": 2},
            },
            "recommendations": [
                "RFE rate on O-1 cases is above average — consider strengthening evidence packets",
                "H-1B processing times improved by 12 days YoY — good momentum",
                "Client satisfaction scores are in the top 12% — leverage for marketing",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_industry_averages(self, year: int = 2025) -> dict:
        return {
            "year": year,
            "approval_rate": 0.89,
            "avg_processing_days": 142,
            "rfe_rate": 0.22,
            "denial_rate": 0.11,
            "avg_filing_volume_per_firm": 120,
            "avg_client_rating": 4.3,
            "data_source": "Verom platform aggregated data",
            "firms_in_sample": 340,
        }

    def compare_to_peers(self, firm_id: str, peer_group: str = "mid-size") -> dict:
        return {
            "firm_id": firm_id,
            "peer_group": peer_group,
            "your_approval_rate": 0.94,
            "peer_avg_approval_rate": 0.91,
            "your_rfe_rate": 0.16,
            "peer_avg_rfe_rate": 0.20,
            "your_avg_processing_days": 130,
            "peer_avg_processing_days": 148,
            "outperforming": ["approval_rate", "rfe_rate", "processing_time"],
            "underperforming": [],
        }

    def export_report(self, firm_id: str, year: int, fmt: str = "json") -> dict:
        report = self.generate_report(firm_id, year)
        return {"format": fmt, "data": report, "download_url": f"/api/benchmark/download/{firm_id}/{year}.{fmt}"}

    def _get_firm_metrics(self, firm_id: str, year: int) -> dict:
        return {
            "filing_volume": 160,
            "approval_rate": 0.94,
            "avg_processing_days": 130,
            "rfe_rate": 0.16,
            "denial_rate": 0.06,
            "client_satisfaction": 4.7,
            "revenue": "varies by firm",
        }


# ---------------------------------------------------------------------------
# 5. Progressive Web App & Offline Mode
# ---------------------------------------------------------------------------

class PWAService:
    """PWA with offline mode and SMS updates for unreliable internet."""

    def get_manifest(self) -> dict:
        return {
            "name": "Verom.ai Immigration Platform",
            "short_name": "Verom",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#6366f1",
            "description": "AI-powered immigration compliance and case management",
            "icons": [
                {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
            "categories": ["business", "productivity"],
            "lang": "en-US",
        }

    def get_service_worker_config(self) -> dict:
        return {
            "cache_strategy": "stale-while-revalidate",
            "cache_name": "verom-v1",
            "precache": ["/", "/app", "/attorney", "/applicant", "/login", "/static/css/styles.css", "/static/css/landing.css", "/static/js/app.js", "/static/js/api.js"],
            "runtime_cache": [
                {"pattern": "/api/cases.*", "strategy": "network-first", "max_age_seconds": 300},
                {"pattern": "/api/regulatory.*", "strategy": "stale-while-revalidate", "max_age_seconds": 3600},
                {"pattern": "/api/global.*", "strategy": "cache-first", "max_age_seconds": 86400},
            ],
            "offline_fallback": "/offline.html",
        }

    def get_offline_data(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "cached_at": datetime.utcnow().isoformat(),
            "cases": [
                {"id": "case-001", "type": "H-1B", "status": "pending", "next_deadline": (date.today() + timedelta(days=15)).isoformat()},
                {"id": "case-002", "type": "I-485", "status": "filed", "next_deadline": (date.today() + timedelta(days=45)).isoformat()},
            ],
            "deadlines": [
                {"case_id": "case-001", "title": "RFE Response Due", "date": (date.today() + timedelta(days=15)).isoformat()},
                {"case_id": "case-002", "title": "Biometrics Appointment", "date": (date.today() + timedelta(days=45)).isoformat()},
            ],
            "contacts": [
                {"name": "Jennifer Park", "role": "attorney", "email": "jpark@example.com"},
            ],
            "offline_capable_actions": ["view_cases", "view_deadlines", "view_documents", "draft_notes"],
        }

    def sync_offline_changes(self, user_id: str, changes: list[dict]) -> dict:
        synced = []
        conflicts = []
        for change in changes:
            synced.append({"change_id": change.get("id", str(uuid.uuid4())), "status": "synced", "server_timestamp": datetime.utcnow().isoformat()})
        return {"user_id": user_id, "total_changes": len(changes), "synced": len(synced), "conflicts": len(conflicts), "details": synced}

    def send_sms_update(self, phone: str, message: str) -> dict:
        return {
            "phone": phone,
            "message": message,
            "status": "queued",
            "message_id": str(uuid.uuid4()),
            "queued_at": datetime.utcnow().isoformat(),
            "estimated_delivery": "within 60 seconds",
        }

    def get_push_subscription(self, user_id: str) -> dict:
        return {
            "user_id": user_id,
            "endpoint": "https://fcm.googleapis.com/fcm/send/...",
            "keys": {"p256dh": "base64-encoded-key", "auth": "base64-encoded-auth"},
            "subscribed_events": ["case_status_change", "deadline_approaching", "message_received", "regulatory_alert"],
        }
