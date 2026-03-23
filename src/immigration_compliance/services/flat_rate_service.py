"""Flat-rate pricing service — counter Alma's consumer-friendly pricing model.

Allows attorneys to offer flat-rate packages alongside hourly billing.
Platform does NOT set prices — attorneys define their own flat-rate packages.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum


class PricingModel(str, Enum):
    HOURLY = "hourly"
    FLAT_RATE = "flat_rate"
    MILESTONE = "milestone"
    HYBRID = "hybrid"  # Flat rate + hourly for unexpected work


class FlatRateService:
    """Manage attorney flat-rate pricing packages."""

    # Template packages attorneys can customize (no specific prices)
    _PACKAGE_TEMPLATES: list[dict] = [
        {
            "template_id": "h1b_standard",
            "visa_type": "H-1B",
            "name": "H-1B Petition Package",
            "included_services": [
                "Initial consultation and case evaluation",
                "LCA filing and certification",
                "H-1B petition preparation and filing",
                "Response to one standard RFE (if issued)",
                "Status monitoring until decision",
            ],
            "excluded_services": [
                "Premium processing fees (government fee paid separately)",
                "Additional RFE responses beyond the first",
                "Appeals or motions to reopen",
                "Change of employer petitions",
            ],
            "typical_complexity": "standard",
            "description": "Complete H-1B petition from start to decision",
        },
        {
            "template_id": "h1b_premium",
            "visa_type": "H-1B",
            "name": "H-1B Premium Package",
            "included_services": [
                "Everything in Standard Package",
                "Premium processing filing",
                "Up to three RFE responses",
                "Dependent H-4/H-4 EAD processing",
                "Post-approval I-94 verification",
            ],
            "excluded_services": [
                "Government filing fees (paid separately)",
                "Appeals or motions",
            ],
            "typical_complexity": "complex",
            "description": "Comprehensive H-1B with premium processing and dependents",
        },
        {
            "template_id": "o1_standard",
            "visa_type": "O-1A",
            "name": "O-1A Extraordinary Ability Package",
            "included_services": [
                "Extraordinary ability criteria analysis",
                "Evidence organization and petition narrative",
                "Advisory opinion coordination",
                "O-1A petition preparation and filing",
                "Response to one RFE",
            ],
            "excluded_services": [
                "Government filing fees",
                "Expert opinion letters (obtained separately)",
                "Additional RFE responses",
                "Premium processing fees",
            ],
            "typical_complexity": "complex",
            "description": "Full O-1A petition with evidence strategy and narrative",
        },
        {
            "template_id": "gc_eb2_standard",
            "visa_type": "Green Card (EB-2)",
            "name": "EB-2 Green Card Package",
            "included_services": [
                "PERM labor certification",
                "I-140 petition preparation and filing",
                "I-485 adjustment of status (when current)",
                "EAD and advance parole applications",
                "Standard RFE responses at each stage",
            ],
            "excluded_services": [
                "Government filing fees at each stage",
                "Premium processing",
                "Recruitment advertising costs",
                "Appeals",
            ],
            "typical_complexity": "complex",
            "description": "Complete EB-2 green card process from PERM through I-485",
        },
        {
            "template_id": "family_i130",
            "visa_type": "Family (I-130)",
            "name": "Family Petition Package",
            "included_services": [
                "I-130 petition preparation and filing",
                "Supporting document review and organization",
                "Affidavit of support preparation (I-864)",
                "Consular processing guidance OR adjustment of status",
                "Interview preparation",
            ],
            "excluded_services": [
                "Government filing fees",
                "Translation services",
                "Medical exam costs",
                "Travel expenses for consular interviews",
            ],
            "typical_complexity": "standard",
            "description": "Family-based immigration petition from filing to interview",
        },
        {
            "template_id": "naturalization",
            "visa_type": "Naturalization (N-400)",
            "name": "Citizenship Application Package",
            "included_services": [
                "Eligibility assessment",
                "N-400 preparation and filing",
                "Document review and organization",
                "Interview preparation and coaching",
                "Oath ceremony guidance",
            ],
            "excluded_services": [
                "Government filing fees",
                "Civics test study materials",
                "English language tutoring",
            ],
            "typical_complexity": "standard",
            "description": "Complete naturalization from application to oath ceremony",
        },
    ]

    def __init__(self) -> None:
        self._attorney_packages: dict[str, list[dict]] = {}  # attorney_id -> packages
        self._engagements: dict[str, dict] = {}  # engagement_id -> engagement

    def get_package_templates(self, visa_type: str | None = None) -> list[dict]:
        """Get package templates attorneys can customize."""
        if visa_type:
            return [t for t in self._PACKAGE_TEMPLATES if visa_type.lower() in t["visa_type"].lower()]
        return self._PACKAGE_TEMPLATES

    def create_attorney_package(self, attorney_id: str, package_data: dict) -> dict:
        """Attorney creates a flat-rate package based on a template or custom."""
        package_id = str(uuid.uuid4())
        package = {
            "id": package_id,
            "attorney_id": attorney_id,
            "template_id": package_data.get("template_id", "custom"),
            "name": package_data.get("name", "Custom Package"),
            "visa_type": package_data.get("visa_type", ""),
            "pricing_model": package_data.get("pricing_model", PricingModel.FLAT_RATE.value),
            "price_display": package_data.get("price_display", "Contact for quote"),
            "included_services": package_data.get("included_services", []),
            "excluded_services": package_data.get("excluded_services", []),
            "estimated_timeline": package_data.get("estimated_timeline", ""),
            "max_active_engagements": package_data.get("max_active", 10),
            "is_published": package_data.get("is_published", False),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        if attorney_id not in self._attorney_packages:
            self._attorney_packages[attorney_id] = []
        self._attorney_packages[attorney_id].append(package)
        return package

    def get_attorney_packages(self, attorney_id: str) -> list[dict]:
        """Get all packages for an attorney."""
        return self._attorney_packages.get(attorney_id, [])

    def get_published_packages(self, visa_type: str | None = None) -> list[dict]:
        """Get all published packages (visible to applicants in marketplace)."""
        all_packages = []
        for packages in self._attorney_packages.values():
            for p in packages:
                if p.get("is_published"):
                    if visa_type and visa_type.lower() not in p.get("visa_type", "").lower():
                        continue
                    all_packages.append(p)
        return all_packages

    def create_engagement(self, package_id: str, applicant_id: str, attorney_id: str) -> dict:
        """Create a flat-rate engagement between applicant and attorney."""
        # Find the package
        package = None
        for packages in self._attorney_packages.values():
            for p in packages:
                if p["id"] == package_id:
                    package = p
                    break

        engagement_id = str(uuid.uuid4())
        engagement = {
            "id": engagement_id,
            "package_id": package_id,
            "package_name": package["name"] if package else "Custom",
            "applicant_id": applicant_id,
            "attorney_id": attorney_id,
            "pricing_model": package.get("pricing_model", "flat_rate") if package else "flat_rate",
            "status": "pending_payment",
            "milestones": self._generate_milestones(package),
            "created_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
        }
        self._engagements[engagement_id] = engagement
        return engagement

    def _generate_milestones(self, package: dict | None) -> list[dict]:
        """Generate payment milestones for a flat-rate engagement."""
        if not package:
            return []

        visa = package.get("visa_type", "").upper()

        if "H-1B" in visa:
            return [
                {"order": 1, "name": "Engagement start", "percentage": 30, "status": "pending", "description": "Due at case acceptance"},
                {"order": 2, "name": "LCA certified", "percentage": 20, "status": "pending", "description": "Released when LCA is certified by DOL"},
                {"order": 3, "name": "Petition filed", "percentage": 30, "status": "pending", "description": "Released when H-1B petition is filed with USCIS"},
                {"order": 4, "name": "Decision received", "percentage": 20, "status": "pending", "description": "Released when USCIS issues decision"},
            ]
        elif "GREEN CARD" in visa or "EB-" in visa:
            return [
                {"order": 1, "name": "Engagement start", "percentage": 20, "status": "pending", "description": "Due at case acceptance"},
                {"order": 2, "name": "PERM filed", "percentage": 20, "status": "pending", "description": "Released when PERM application is filed"},
                {"order": 3, "name": "PERM certified", "percentage": 20, "status": "pending", "description": "Released when PERM is certified"},
                {"order": 4, "name": "I-140 filed", "percentage": 20, "status": "pending", "description": "Released when I-140 is filed"},
                {"order": 5, "name": "I-485 filed/Decision", "percentage": 20, "status": "pending", "description": "Released at final stage"},
            ]
        else:
            return [
                {"order": 1, "name": "Engagement start", "percentage": 40, "status": "pending", "description": "Due at case acceptance"},
                {"order": 2, "name": "Filing submitted", "percentage": 30, "status": "pending", "description": "Released when application is filed"},
                {"order": 3, "name": "Decision received", "percentage": 30, "status": "pending", "description": "Released when decision is received"},
            ]

    def get_engagement(self, engagement_id: str) -> dict | None:
        return self._engagements.get(engagement_id)

    def advance_milestone(self, engagement_id: str, milestone_order: int) -> dict | None:
        """Mark a milestone as completed, triggering escrow release."""
        engagement = self._engagements.get(engagement_id)
        if not engagement:
            return None

        for m in engagement["milestones"]:
            if m["order"] == milestone_order:
                m["status"] = "completed"
                m["completed_at"] = datetime.utcnow().isoformat()
                break

        # Check if all milestones complete
        if all(m["status"] == "completed" for m in engagement["milestones"]):
            engagement["status"] = "completed"
            engagement["completed_at"] = datetime.utcnow().isoformat()

        return engagement

    def compare_pricing_models(self) -> dict:
        """Help applicants understand flat-rate vs hourly pricing."""
        return {
            "flat_rate": {
                "pros": [
                    "Know your total cost upfront — no surprises",
                    "Attorney absorbs risk of unexpected complications",
                    "Easier to budget and plan",
                    "Aligned incentives — attorney wants to resolve efficiently",
                ],
                "cons": [
                    "May cost more than hourly for simple, fast cases",
                    "Scope limitations — excluded services cost extra",
                    "Not all attorneys offer flat rates",
                ],
                "best_for": "Straightforward cases with predictable scope (H-1B, family petitions, naturalization)",
            },
            "hourly": {
                "pros": [
                    "Pay only for time actually spent",
                    "More flexibility for complex, evolving cases",
                    "Can be cheaper for simple cases resolved quickly",
                ],
                "cons": [
                    "Unpredictable total cost",
                    "Risk of bill shock from RFEs or complications",
                    "May create misaligned incentives",
                ],
                "best_for": "Complex cases with uncertain scope (asylum, deportation defense, multi-stage processes)",
            },
            "milestone": {
                "pros": [
                    "Payment tied to progress — you pay as work is completed",
                    "Protection through escrow — funds held until milestones verified",
                    "Transparency — see exactly where your money goes",
                ],
                "cons": [
                    "Slightly higher total cost than pure flat-rate (escrow processing)",
                ],
                "best_for": "Any case on the Verom platform — our recommended model for maximum protection",
            },
            "verom_recommendation": "Milestone-based pricing with escrow protection gives you the predictability of flat-rate pricing with the accountability of progress-based payments. All Verom engagements include escrow protection regardless of pricing model.",
        }
