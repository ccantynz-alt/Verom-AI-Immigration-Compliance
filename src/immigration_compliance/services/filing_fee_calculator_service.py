"""Filing Fee Calculator — auto-updated agency fee schedules.

Every immigration form has a filing fee that changes when USCIS / DOL / DOS /
EOIR publish new fee schedules. The platform should never quote a stale fee.

This service:
  - Maintains a versioned fee schedule per form, per agency, per effective date
  - Computes the total filing-fee bill for a single petition or a family bundle
  - Surfaces fee waivers, reduced fees, premium-processing add-ons, biometric
    fees, and the asylum-program fee
  - Returns a citation per fee so attorneys can verify against the official
    USCIS Fee Schedule (G-1055) or the relevant Federal Register notice

Seed corpus is the April 1, 2024 USCIS fee rule (the largest fee restructuring
in 2 decades) plus DOL ETA-9089 / DOS DS-160 fees current as of 2025-2026.
Drop-in replacement: register_schedule_loader() for live fee feeds.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any


# Seed fee schedule — every entry carries effective_date so the calculator
# returns the fee in effect on the calculation date.
# All values in USD. Source columns: "Online" vs "Paper" filing where relevant.
SEED_FEE_SCHEDULE: list[dict[str, Any]] = [
    # ----- USCIS forms (April 1 2024 rule) -----
    {
        "form": "I-129",
        "category": "H-1B (named beneficiary)",
        "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 780,
        "asylum_program_fee_usd": 600,         # standard employer
        "asylum_program_fee_small_usd": 300,   # small employer (≤25 FTE)
        "asylum_program_fee_nonprofit_usd": 0,
        "premium_processing_usd": 2805,
        "biometric_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-129", "category": "L-1", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 1385,
        "asylum_program_fee_usd": 600,
        "asylum_program_fee_small_usd": 300,
        "premium_processing_usd": 2805,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-129", "category": "O-1", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 1055,
        "asylum_program_fee_usd": 600,
        "asylum_program_fee_small_usd": 300,
        "premium_processing_usd": 2805,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-129", "category": "TN/E/H-3", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 1015,
        "asylum_program_fee_usd": 600,
        "asylum_program_fee_small_usd": 300,
        "premium_processing_usd": 2805,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-130", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 675,    # paper
        "filing_fee_online_usd": 625,
        "biometric_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-140", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 715,
        "asylum_program_fee_usd": 600,
        "asylum_program_fee_small_usd": 300,
        "premium_processing_usd": 2805,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-485", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 1440,    # adult, no longer bundled with I-765/I-131
        "filing_fee_under_14_usd": 950,
        "biometric_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-765", "category": "Initial EAD", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 520,    # paper
        "filing_fee_online_usd": 470,
        "filing_fee_with_485_usd": 260,    # filed concurrently with I-485
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-131", "category": "Advance Parole", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 630,
        "filing_fee_with_485_usd": 630,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-539", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 470,    # paper
        "filing_fee_online_usd": 420,
        "biometric_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-589", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 0,    # asylum is free under TRAIG
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-751", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 750,
        "biometric_fee_usd": 0,    # bundled
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "N-400", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 760,    # paper
        "filing_fee_online_usd": 710,
        "filing_fee_reduced_usd": 380,    # 150-200% federal poverty
        "biometric_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-360", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 515,
        "asylum_program_fee_usd": 600,
        "asylum_program_fee_small_usd": 300,
        "asylum_program_fee_nonprofit_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-526E", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 11160,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "I-829", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 9525,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    {
        "form": "G-28", "agency": "USCIS",
        "effective_date": "2024-04-01",
        "filing_fee_usd": 0,
        "citation": "USCIS Fee Schedule G-1055 (Apr 1 2024)",
    },
    # ----- DOL forms -----
    {
        "form": "ETA-9089", "category": "PERM", "agency": "DOL",
        "effective_date": "2023-06-01",
        "filing_fee_usd": 0,    # PERM filing itself is free; H-2B has fees
        "citation": "DOL Foreign Labor Certification — PERM",
    },
    {
        "form": "ETA-9035", "category": "LCA", "agency": "DOL",
        "effective_date": "2023-06-01",
        "filing_fee_usd": 0,
        "citation": "DOL Foreign Labor Certification — LCA",
    },
    # ----- DOS forms -----
    {
        "form": "DS-160", "agency": "DOS",
        "effective_date": "2023-06-17",
        "filing_fee_usd": 185,    # H, L, O, P, Q, R nonimmigrant
        "filing_fee_visitor_usd": 185,    # B, C-1, D, F, J, M
        "filing_fee_e_usd": 315,
        "filing_fee_k_usd": 265,
        "citation": "DOS Schedule of Fees (22 CFR 22.1)",
    },
    {
        "form": "DS-260", "agency": "DOS",
        "effective_date": "2023-06-17",
        "filing_fee_usd": 325,    # immigrant visa application
        "affidavit_of_support_review_usd": 120,
        "citation": "DOS Schedule of Fees (22 CFR 22.1)",
    },
    # ----- EOIR forms -----
    {
        "form": "EOIR-26", "category": "BIA Appeal", "agency": "EOIR",
        "effective_date": "2024-12-18",
        "filing_fee_usd": 800,
        "citation": "EOIR Fee Increase Final Rule (Dec 18 2024)",
    },
    {
        "form": "EOIR-29", "category": "Appeal of DHS Officer Decision", "agency": "EOIR",
        "effective_date": "2024-12-18",
        "filing_fee_usd": 800,
        "citation": "EOIR Fee Increase Final Rule (Dec 18 2024)",
    },
    {
        "form": "EOIR-42A", "category": "Cancellation of Removal (LPR)", "agency": "EOIR",
        "effective_date": "2024-12-18",
        "filing_fee_usd": 305,
        "citation": "EOIR Fee Increase Final Rule (Dec 18 2024)",
    },
    {
        "form": "EOIR-42B", "category": "Cancellation of Removal (Non-LPR)", "agency": "EOIR",
        "effective_date": "2024-12-18",
        "filing_fee_usd": 360,
        "citation": "EOIR Fee Increase Final Rule (Dec 18 2024)",
    },
]


EMPLOYER_SIZES = ("standard", "small", "nonprofit", "research_org", "fee_exempt")


# ---------------------------------------------------------------------------

class FilingFeeCalculatorService:
    """Compute filing-fee totals from a hand-curated, dated fee schedule."""

    def __init__(self) -> None:
        self._schedule: list[dict[str, Any]] = list(SEED_FEE_SCHEDULE)
        self._calculations: dict[str, dict] = {}
        self._loader = None

    # ---------- introspection ----------
    def list_forms(self, agency: str | None = None) -> list[str]:
        out = self._schedule
        if agency:
            out = [r for r in out if r["agency"].upper() == agency.upper()]
        return sorted({r["form"] for r in out})

    def list_agencies(self) -> list[str]:
        return sorted({r["agency"] for r in self._schedule})

    def lookup_schedule(
        self, form: str, category: str | None = None,
        as_of: str | None = None,
    ) -> dict | None:
        as_of = as_of or date.today().isoformat()
        candidates = [
            r for r in self._schedule
            if r["form"] == form
            and r["effective_date"] <= as_of
            and (not category or r.get("category", "").lower() == category.lower())
        ]
        if not candidates and category:
            # Fallback: any matching form, ignore category
            candidates = [
                r for r in self._schedule
                if r["form"] == form and r["effective_date"] <= as_of
            ]
        if not candidates:
            return None
        # Newest effective entry that's still ≤ as_of
        return max(candidates, key=lambda r: r["effective_date"])

    # ---------- single-form calculation ----------
    def calculate(
        self,
        form: str,
        category: str | None = None,
        employer_size: str = "standard",
        filed_online: bool = False,
        with_premium_processing: bool = False,
        filed_with_i485: bool = False,
        applicant_age: int | None = None,
        as_of: str | None = None,
        fee_waiver_eligible: bool = False,
    ) -> dict:
        if employer_size not in EMPLOYER_SIZES:
            raise ValueError(f"Unknown employer_size: {employer_size}")
        as_of = as_of or date.today().isoformat()
        schedule = self.lookup_schedule(form, category=category, as_of=as_of)
        if schedule is None:
            raise ValueError(f"No fee schedule for form={form} category={category} as_of={as_of}")

        line_items: list[dict] = []

        # Fee waiver short-circuits (some forms only)
        if fee_waiver_eligible:
            line_items.append({
                "label": f"{form} fee waiver (Form I-912)",
                "amount_usd": 0,
                "note": "Fee waived per I-912 approval; verify approval letter on file",
            })
            total = 0
        else:
            # Base filing fee
            base_fee = schedule["filing_fee_usd"]
            if filed_online and "filing_fee_online_usd" in schedule:
                base_fee = schedule["filing_fee_online_usd"]
            if filed_with_i485 and "filing_fee_with_485_usd" in schedule:
                base_fee = schedule["filing_fee_with_485_usd"]
            if (
                form == "I-485" and applicant_age is not None
                and applicant_age < 14
                and "filing_fee_under_14_usd" in schedule
            ):
                base_fee = schedule["filing_fee_under_14_usd"]
            line_items.append({
                "label": f"{form} filing fee" + (" (online)" if filed_online else ""),
                "amount_usd": base_fee,
            })

            # Asylum program fee (large rebalance in the 2024 rule)
            if "asylum_program_fee_usd" in schedule and employer_size != "fee_exempt":
                if employer_size == "small":
                    apf = schedule.get("asylum_program_fee_small_usd",
                                       schedule["asylum_program_fee_usd"])
                elif employer_size == "nonprofit":
                    apf = schedule.get("asylum_program_fee_nonprofit_usd", 0)
                elif employer_size == "research_org":
                    apf = schedule.get("asylum_program_fee_nonprofit_usd",
                                       schedule.get("asylum_program_fee_small_usd",
                                                    schedule["asylum_program_fee_usd"]))
                else:
                    apf = schedule["asylum_program_fee_usd"]
                if apf:
                    line_items.append({
                        "label": "Asylum Program Fee",
                        "amount_usd": apf,
                        "note": f"Tiered by employer size: {employer_size}",
                    })

            # Biometrics
            if schedule.get("biometric_fee_usd"):
                line_items.append({
                    "label": "Biometric services fee",
                    "amount_usd": schedule["biometric_fee_usd"],
                })

            # Premium processing
            if with_premium_processing and "premium_processing_usd" in schedule:
                line_items.append({
                    "label": "Premium processing (I-907)",
                    "amount_usd": schedule["premium_processing_usd"],
                    "note": "15-business-day adjudication clock starts at receipt",
                })

            total = sum(li["amount_usd"] for li in line_items)

        calc_id = str(uuid.uuid4())
        record = {
            "id": calc_id,
            "form": form,
            "category": category,
            "agency": schedule["agency"],
            "as_of": as_of,
            "schedule_effective_date": schedule["effective_date"],
            "filed_online": filed_online,
            "with_premium_processing": with_premium_processing,
            "filed_with_i485": filed_with_i485,
            "employer_size": employer_size,
            "applicant_age": applicant_age,
            "fee_waiver_eligible": fee_waiver_eligible,
            "line_items": line_items,
            "total_usd": total,
            "citation": schedule["citation"],
            "computed_at": datetime.utcnow().isoformat(),
            "disclosure": (
                "Computed from the USCIS / DOL / DOS / EOIR fee schedule cached "
                "in the platform. Always verify against the official agency fee "
                "page before tendering payment — fees change."
            ),
        }
        self._calculations[calc_id] = record
        return record

    # ---------- bundle / family calculation ----------
    def calculate_bundle(
        self,
        forms: list[dict[str, Any]],
        as_of: str | None = None,
    ) -> dict:
        """Compute total fees for a list of form-arg dicts.

        Each item in `forms` is a kwargs dict for `calculate()`.
        Useful for family-based filings (I-130 + I-485 + I-765 + I-131) or
        for an H-1B + dependent I-539s.
        """
        results = []
        total = 0
        for item in forms:
            r = self.calculate(as_of=as_of, **item)
            results.append(r)
            total += r["total_usd"]
        return {
            "as_of": as_of or date.today().isoformat(),
            "form_count": len(results),
            "results": results,
            "total_usd": total,
            "computed_at": datetime.utcnow().isoformat(),
        }

    # ---------- audit ----------
    def get_calculation(self, calc_id: str) -> dict | None:
        return self._calculations.get(calc_id)

    def list_calculations(self, limit: int = 100) -> list[dict]:
        return list(self._calculations.values())[-limit:]

    # ---------- live loader registration ----------
    def register_schedule_loader(self, loader: Any) -> None:
        """Pluggable boundary for live fee feeds (e.g. scraping G-1055)."""
        self._loader = loader

    def reload_from_loader(self) -> int:
        if self._loader is None:
            return 0
        new_entries = self._loader()
        added = 0
        for entry in new_entries:
            # Skip duplicates by (form, category, effective_date)
            key = (entry["form"], entry.get("category"), entry["effective_date"])
            existing_keys = {
                (e["form"], e.get("category"), e["effective_date"])
                for e in self._schedule
            }
            if key not in existing_keys:
                self._schedule.append(entry)
                added += 1
        return added
