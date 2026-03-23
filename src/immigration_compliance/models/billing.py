"""Billing and subscription models for Stripe integration."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class PlanTier(str, Enum):
    """Subscription tiers."""
    # Attorney plans
    ATTORNEY_SOLO = "attorney_solo"
    ATTORNEY_FIRM = "attorney_firm"
    ATTORNEY_ENTERPRISE = "attorney_enterprise"
    # Employer plans
    EMPLOYER_STARTER = "employer_starter"
    EMPLOYER_BUSINESS = "employer_business"
    EMPLOYER_ENTERPRISE = "employer_enterprise"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"


class PlanInfo(BaseModel):
    """Product/plan details shown to users."""
    tier: PlanTier
    name: str
    description: str
    features: list[str]
    # No specific dollar amounts per CLAUDE.md legal safeguards
    price_label: str  # e.g. "Contact us", "Starting at..."


class Subscription(BaseModel):
    id: str
    user_id: str
    plan: PlanTier
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    stripe_subscription_id: str = ""
    stripe_customer_id: str = ""


class CreateCheckoutRequest(BaseModel):
    """Request to create a Stripe Checkout session."""
    plan: PlanTier
    success_url: str = ""
    cancel_url: str = ""


class CheckoutResponse(BaseModel):
    """Redirect URL for Stripe Checkout."""
    checkout_url: str
    session_id: str


class ConnectOnboardRequest(BaseModel):
    """Request to start Stripe Connect onboarding for attorneys."""
    return_url: str = ""
    refresh_url: str = ""


class ConnectOnboardResponse(BaseModel):
    """Redirect URL for Stripe Connect onboarding."""
    onboarding_url: str
    account_id: str


class PaymentIntentRequest(BaseModel):
    """Request to create a payment from applicant to attorney."""
    attorney_user_id: str
    case_id: str
    description: str = ""


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount_display: str
