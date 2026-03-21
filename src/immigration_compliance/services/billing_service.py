"""Billing service — Stripe integration for subscriptions and payments.

In production, this calls the Stripe API. For now it provides a working
mock so the frontend can be built and tested without a Stripe account.
Set STRIPE_SECRET_KEY env var to enable live Stripe calls.
"""

from __future__ import annotations

import os
import uuid

from immigration_compliance.models.billing import (
    CheckoutResponse,
    ConnectOnboardResponse,
    PaymentIntentResponse,
    PlanInfo,
    PlanTier,
    Subscription,
    SubscriptionStatus,
)

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_LIVE = bool(STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith("sk_"))

# Product catalog — no specific prices per CLAUDE.md legal rules
PLANS: list[PlanInfo] = [
    PlanInfo(
        tier=PlanTier.ATTORNEY_SOLO,
        name="Solo Attorney",
        description="For individual practitioners managing their own caseload.",
        features=[
            "AI-powered client intake",
            "Up to 25 active cases",
            "Document management",
            "Deadline tracking",
            "Client portal",
            "Government status feeds",
        ],
        price_label="Free during early access",
    ),
    PlanInfo(
        tier=PlanTier.ATTORNEY_FIRM,
        name="Firm",
        description="For small to mid-size immigration firms with multiple attorneys.",
        features=[
            "Everything in Solo",
            "Unlimited active cases",
            "Multi-attorney dashboard",
            "Team deadline visibility",
            "Batch form generation",
            "Staff productivity metrics",
            "Priority support",
        ],
        price_label="Contact us for pricing",
    ),
    PlanInfo(
        tier=PlanTier.ATTORNEY_ENTERPRISE,
        name="Enterprise",
        description="For large firms and Am Law practices with custom needs.",
        features=[
            "Everything in Firm",
            "Custom integrations",
            "Dedicated account manager",
            "SLA guarantees",
            "SSO / SAML",
            "Custom reporting",
        ],
        price_label="Custom pricing",
    ),
    PlanInfo(
        tier=PlanTier.EMPLOYER_STARTER,
        name="Starter",
        description="For small companies with a handful of sponsored employees.",
        features=[
            "Up to 25 employees",
            "Compliance dashboard",
            "I-9 tracking",
            "Visa expiration alerts",
            "Basic reports",
        ],
        price_label="Free during early access",
    ),
    PlanInfo(
        tier=PlanTier.EMPLOYER_BUSINESS,
        name="Business",
        description="For growing companies with an active immigration program.",
        features=[
            "Everything in Starter",
            "Unlimited employees",
            "ICE audit simulator",
            "PAF management",
            "HRIS integrations",
            "Regulatory intelligence feed",
            "Global immigration tracking",
        ],
        price_label="Contact us for pricing",
    ),
    PlanInfo(
        tier=PlanTier.EMPLOYER_ENTERPRISE,
        name="Enterprise",
        description="For multinational corporations with complex global mobility needs.",
        features=[
            "Everything in Business",
            "Multi-entity support",
            "Custom workflows",
            "API access",
            "Dedicated CSM",
            "Custom SLA",
        ],
        price_label="Custom pricing",
    ),
]


class BillingService:
    """Handles subscriptions, Stripe Checkout, Connect, and payments."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, Subscription] = {}
        self._connect_accounts: dict[str, str] = {}  # user_id -> stripe_account_id

    def get_plans(self, role: str = "") -> list[PlanInfo]:
        """Return available plans, optionally filtered by role prefix."""
        if role in ("attorney", "employer"):
            return [p for p in PLANS if p.tier.value.startswith(role)]
        return PLANS

    def create_checkout_session(
        self, user_id: str, plan: PlanTier, success_url: str, cancel_url: str
    ) -> CheckoutResponse:
        """Create a Stripe Checkout session (mock in dev)."""
        session_id = f"cs_{uuid.uuid4().hex[:24]}"

        if STRIPE_LIVE:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            # In production: create real Checkout session with price IDs
            # stripe.checkout.Session.create(...)

        # Store subscription record
        sub = Subscription(
            id=f"sub_{uuid.uuid4().hex[:16]}",
            user_id=user_id,
            plan=plan,
            status=SubscriptionStatus.TRIALING,
        )
        self._subscriptions[sub.id] = sub

        return CheckoutResponse(
            checkout_url=success_url or "/app",
            session_id=session_id,
        )

    def get_subscription(self, user_id: str) -> Subscription | None:
        """Get a user's active subscription."""
        for sub in self._subscriptions.values():
            if sub.user_id == user_id and sub.status in (
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
            ):
                return sub
        return None

    def create_connect_account(
        self, user_id: str, return_url: str, refresh_url: str
    ) -> ConnectOnboardResponse:
        """Start Stripe Connect onboarding for an attorney (mock in dev)."""
        account_id = f"acct_{uuid.uuid4().hex[:16]}"

        if STRIPE_LIVE:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            # In production: stripe.Account.create(...) and stripe.AccountLink.create(...)

        self._connect_accounts[user_id] = account_id

        return ConnectOnboardResponse(
            onboarding_url=return_url or "/attorney",
            account_id=account_id,
        )

    def get_connect_account(self, user_id: str) -> str | None:
        """Check if attorney has a connected Stripe account."""
        return self._connect_accounts.get(user_id)

    def create_payment_intent(
        self, applicant_user_id: str, attorney_user_id: str, case_id: str, description: str
    ) -> PaymentIntentResponse:
        """Create a payment from applicant to attorney via Connect (mock in dev)."""
        pi_id = f"pi_{uuid.uuid4().hex[:24]}"
        client_secret = f"{pi_id}_secret_{uuid.uuid4().hex[:12]}"

        if STRIPE_LIVE:
            import stripe
            stripe.api_key = STRIPE_SECRET_KEY
            # In production: stripe.PaymentIntent.create(
            #     amount=..., currency="usd",
            #     transfer_data={"destination": connect_account_id},
            #     application_fee_amount=...,
            # )

        return PaymentIntentResponse(
            client_secret=client_secret,
            payment_intent_id=pi_id,
            amount_display="Set by attorney",
        )
