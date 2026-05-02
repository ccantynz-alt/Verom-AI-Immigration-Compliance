"""Local Payment Methods Registry — country-aware checkout adapters.

Without local payment methods, conversion rates in non-US markets cap at 30%.
This service is the registry + checkout-session abstraction that lets the
platform offer Pix in Brazil, UPI in India, Alipay/WeChat in China, SEPA in
Europe, etc. — alongside Stripe / LawPay for the US.

Each method declares:
  - ISO countries it serves
  - Currencies it settles in
  - Provider it routes through (Stripe / Adyen / Razorpay / Alipay / etc.)
  - Settlement timeline (T+0, T+1, T+2)
  - Refund support
  - Trust-account compatibility (which methods are bar-compliant for IOLTA?)

Provider boundaries are pluggable. Production hooks each method to a real
provider session-creation call. This implementation provides a deterministic
mock that returns shaped checkout URLs for testing the full flow.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Method registry
# ---------------------------------------------------------------------------

METHODS: dict[str, dict[str, Any]] = {
    "stripe_card": {
        "label": "Credit / Debit Card (Stripe)",
        "provider": "stripe",
        "iso_countries": ["US", "CA", "GB", "AU", "DE", "FR", "NL", "SG", "JP",
                          "MX", "BR", "AE", "IE", "ES", "IT", "PL", "PT"],
        "currencies": ["USD", "CAD", "GBP", "AUD", "EUR", "SGD", "JPY", "MXN",
                       "BRL", "AED", "PLN"],
        "settlement_days": 2,
        "supports_refund": True,
        "iolta_compatible": True,
        "fee_pct": 2.9,
    },
    "lawpay_card": {
        "label": "LawPay (bar-compliant trust account)",
        "provider": "lawpay",
        "iso_countries": ["US"],
        "currencies": ["USD"],
        "settlement_days": 2,
        "supports_refund": True,
        "iolta_compatible": True,
        "fee_pct": 1.95,
        "trust_account_certified": True,
    },
    "ach_us": {
        "label": "ACH (US bank transfer)",
        "provider": "stripe",
        "iso_countries": ["US"],
        "currencies": ["USD"],
        "settlement_days": 5,
        "supports_refund": True,
        "iolta_compatible": True,
        "fee_pct": 0.8,
    },
    "wire_us": {
        "label": "US wire transfer",
        "provider": "manual",
        "iso_countries": ["US"],
        "currencies": ["USD"],
        "settlement_days": 1,
        "supports_refund": False,
        "iolta_compatible": True,
        "fee_pct": 0.0,
    },
    "pix": {
        "label": "Pix (Brazil)",
        "provider": "adyen",
        "iso_countries": ["BR"],
        "currencies": ["BRL"],
        "settlement_days": 0,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 1.5,
    },
    "boleto": {
        "label": "Boleto Bancário (Brazil)",
        "provider": "adyen",
        "iso_countries": ["BR"],
        "currencies": ["BRL"],
        "settlement_days": 2,
        "supports_refund": False,
        "iolta_compatible": False,
        "fee_pct": 1.5,
    },
    "upi": {
        "label": "UPI (India)",
        "provider": "razorpay",
        "iso_countries": ["IN"],
        "currencies": ["INR"],
        "settlement_days": 1,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 0.6,
    },
    "razorpay_card": {
        "label": "Razorpay card (India)",
        "provider": "razorpay",
        "iso_countries": ["IN"],
        "currencies": ["INR"],
        "settlement_days": 2,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 2.0,
    },
    "alipay": {
        "label": "Alipay (China)",
        "provider": "alipay",
        "iso_countries": ["CN", "HK", "SG", "TW", "AU", "GB"],
        "currencies": ["CNY", "USD", "HKD", "AUD", "GBP", "EUR"],
        "settlement_days": 1,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 2.5,
    },
    "wechat_pay": {
        "label": "WeChat Pay (China)",
        "provider": "wechat",
        "iso_countries": ["CN", "HK"],
        "currencies": ["CNY", "USD", "HKD"],
        "settlement_days": 1,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 2.5,
    },
    "sepa_debit": {
        "label": "SEPA Direct Debit (EU)",
        "provider": "stripe",
        "iso_countries": ["DE", "FR", "NL", "ES", "IT", "PT", "AT", "BE", "IE"],
        "currencies": ["EUR"],
        "settlement_days": 5,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 0.8,
    },
    "ideal": {
        "label": "iDEAL (Netherlands)",
        "provider": "stripe",
        "iso_countries": ["NL"],
        "currencies": ["EUR"],
        "settlement_days": 1,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 0.3,
    },
    "bacs_debit": {
        "label": "BACS Direct Debit (UK)",
        "provider": "stripe",
        "iso_countries": ["GB"],
        "currencies": ["GBP"],
        "settlement_days": 7,
        "supports_refund": True,
        "iolta_compatible": False,
        "fee_pct": 1.0,
    },
    "interac": {
        "label": "Interac e-Transfer (Canada)",
        "provider": "stripe",
        "iso_countries": ["CA"],
        "currencies": ["CAD"],
        "settlement_days": 1,
        "supports_refund": False,
        "iolta_compatible": False,
        "fee_pct": 1.0,
    },
    "paynow": {
        "label": "PayNow (Singapore)",
        "provider": "stripe",
        "iso_countries": ["SG"],
        "currencies": ["SGD"],
        "settlement_days": 0,
        "supports_refund": False,
        "iolta_compatible": False,
        "fee_pct": 0.5,
    },
}

CHECKOUT_INTENTS = ("retainer", "consultation_fee", "filing_fee_passthrough",
                    "platform_fee", "milestone_payment", "refund")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class LocalPaymentsService:
    """Per-country checkout adapter registry."""

    def __init__(
        self,
        provider_dispatchers: dict[str, Callable] | None = None,
    ) -> None:
        self._dispatchers = provider_dispatchers or {}
        self._sessions: dict[str, dict] = {}
        # Also stash a default mock for any unwired providers
        for method_id, method in METHODS.items():
            provider = method["provider"]
            self._dispatchers.setdefault(provider, self._stub_dispatch)

    # ---------- introspection ----------
    @staticmethod
    def list_methods(country: str | None = None, currency: str | None = None,
                      iolta_compatible: bool | None = None) -> list[dict]:
        out = []
        for mid, m in METHODS.items():
            if country and country.upper() not in m["iso_countries"]:
                continue
            if currency and currency.upper() not in m["currencies"]:
                continue
            if iolta_compatible is not None and m.get("iolta_compatible", False) != iolta_compatible:
                continue
            out.append({"id": mid, **m})
        return out

    @staticmethod
    def get_method(method_id: str) -> dict | None:
        m = METHODS.get(method_id)
        if m is None:
            return None
        return {"id": method_id, **m}

    @staticmethod
    def methods_for_country(country: str) -> list[dict]:
        return LocalPaymentsService.list_methods(country=country)

    # ---------- checkout sessions ----------
    def create_checkout_session(
        self,
        method_id: str,
        amount_minor_units: int,    # cents / paise / fen / yen
        currency: str,
        intent: str,
        applicant_user_id: str | None = None,
        attorney_id: str | None = None,
        workspace_id: str | None = None,
        return_url: str | None = None,
        cancel_url: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        method = METHODS.get(method_id)
        if method is None:
            raise ValueError(f"Unknown payment method: {method_id}")
        if intent not in CHECKOUT_INTENTS:
            raise ValueError(f"Unknown checkout intent: {intent}")
        if amount_minor_units <= 0:
            raise ValueError("Amount must be positive")
        if currency.upper() not in method["currencies"]:
            raise ValueError(f"Method {method_id} does not support currency {currency}")
        if intent in ("retainer", "filing_fee_passthrough") and not method.get("iolta_compatible", False):
            # Trust-account-bound payments must use a bar-compliant method
            raise ValueError(
                f"Method {method_id} is not IOLTA-compatible; use a bar-compliant method "
                "(stripe_card, lawpay_card, ach_us, or wire_us) for retainer / filing-fee payments"
            )

        provider = method["provider"]
        dispatcher = self._dispatchers.get(provider, self._stub_dispatch)
        session_id = str(uuid.uuid4())
        try:
            provider_response = dispatcher(
                method_id=method_id, amount_minor_units=amount_minor_units,
                currency=currency, intent=intent,
                applicant_user_id=applicant_user_id, attorney_id=attorney_id,
                workspace_id=workspace_id, return_url=return_url, cancel_url=cancel_url,
                metadata=metadata,
            )
        except Exception as e:
            return {
                "id": session_id, "status": "failed", "error": str(e),
                "method_id": method_id,
            }
        record = {
            "id": session_id,
            "method_id": method_id,
            "provider": provider,
            "amount_minor_units": amount_minor_units,
            "currency": currency,
            "intent": intent,
            "applicant_user_id": applicant_user_id,
            "attorney_id": attorney_id,
            "workspace_id": workspace_id,
            "return_url": return_url, "cancel_url": cancel_url,
            "metadata": metadata or {},
            "checkout_url": provider_response.get("checkout_url"),
            "provider_session_id": provider_response.get("provider_session_id"),
            "status": "open",
            "fee_pct": method.get("fee_pct"),
            "estimated_fee_minor_units": int(amount_minor_units * method.get("fee_pct", 0) / 100),
            "expected_settlement_days": method.get("settlement_days"),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._sessions[session_id] = record
        return record

    def confirm_payment(self, session_id: str, provider_payload: dict) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        session["status"] = "completed"
        session["provider_payload"] = provider_payload
        session["completed_at"] = datetime.utcnow().isoformat()
        return session

    def fail_payment(self, session_id: str, reason: str) -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        session["status"] = "failed"
        session["failure_reason"] = reason
        session["failed_at"] = datetime.utcnow().isoformat()
        return session

    def refund(self, session_id: str, reason: str = "") -> dict:
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError("Session not found")
        method = METHODS.get(session["method_id"])
        if not method or not method.get("supports_refund", False):
            raise ValueError(f"Method {session['method_id']} does not support refunds")
        if session["status"] != "completed":
            raise ValueError(f"Cannot refund session in {session['status']} state")
        session["status"] = "refunded"
        session["refund_reason"] = reason
        session["refunded_at"] = datetime.utcnow().isoformat()
        return session

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def list_sessions(
        self, status: str | None = None,
        attorney_id: str | None = None,
        applicant_user_id: str | None = None,
    ) -> list[dict]:
        out = list(self._sessions.values())
        if status:
            out = [s for s in out if s["status"] == status]
        if attorney_id:
            out = [s for s in out if s.get("attorney_id") == attorney_id]
        if applicant_user_id:
            out = [s for s in out if s.get("applicant_user_id") == applicant_user_id]
        return out

    # ---------- introspection ----------
    @staticmethod
    def list_supported_countries() -> list[str]:
        out = set()
        for m in METHODS.values():
            out.update(m["iso_countries"])
        return sorted(out)

    @staticmethod
    def list_intents() -> list[str]:
        return list(CHECKOUT_INTENTS)

    # ---------- dispatcher hooks ----------
    @staticmethod
    def _stub_dispatch(**kwargs: Any) -> dict:
        return {
            "checkout_url": f"/checkout/mock/{uuid.uuid4().hex[:12]}",
            "provider_session_id": f"mock_sess_{uuid.uuid4().hex[:16]}",
        }

    def register_provider(self, provider: str, dispatcher: Callable) -> None:
        self._dispatchers[provider] = dispatcher
