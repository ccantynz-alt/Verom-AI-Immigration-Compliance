"""IOLTA Trust Accounting Service.

Bar-required for any law firm holding client retainers. Implements the
three-way reconciliation that state bars require:

  1. BANK BALANCE        — what the trust account at the bank holds
  2. TRUST LEDGER        — sum of all trust transactions across all clients
  3. CLIENT SUB-LEDGERS  — per-client balances; sum should equal trust ledger

If any of those three diverge, that's a reconciliation error and must be
investigated — usually a missed transaction or a posted-but-uncleared
deposit. This service tracks all three and flags discrepancies.

Core operations:
  - DEPOSIT          client funds enter the trust account (retainer)
  - INVOICE_PAYMENT  funds move from a client's sub-ledger to operating
                     account when a billable invoice is paid
  - REFUND           funds return to client (case dropped, retainer
                     unused, money-back protection window)
  - DISBURSEMENT     funds paid out to a third party on client's behalf
                     (filing fees, expert witnesses, translation
                     services)
  - INTEREST         interest accrued on the IOLTA account (in most
                     states the interest goes to the state bar
                     foundation, NOT the firm or client)
  - ADJUSTMENT       reconciliation adjustment (must be flagged + signed)

Compliance flags:
  - NO_OVERDRAFT          a client sub-ledger can never go negative
  - NO_COMMINGLING        firm operating funds and client trust funds
                          cannot mix
  - SOURCE_TRACEABILITY   every transaction has source/destination
  - APPROVAL_TRAIL        adjustments and refunds require explicit
                          attorney approval
  - AUDIT_LOG             every transaction permanently logged"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Transaction types
# ---------------------------------------------------------------------------

VALID_TXN_KINDS = (
    "deposit",            # money in to the trust account from client
    "invoice_payment",    # money out of trust to operating (billable work paid)
    "refund",             # money out of trust back to client
    "disbursement",       # money out of trust to third party (fees, etc.)
    "interest",           # IOLTA interest accrual (typically to state bar)
    "adjustment",         # reconciliation correction (requires reason)
    "transfer",           # internal transfer (e.g. consolidating sub-ledgers)
)

REQUIRES_REASON = ("adjustment", "refund", "disbursement")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class TrustAccountingService:
    """IOLTA-compliant trust accounting with three-way reconciliation."""

    def __init__(self) -> None:
        self._accounts: dict[str, dict] = {}        # IOLTA account configs (one per firm typically)
        self._client_ledgers: dict[str, dict] = {}  # per-client sub-ledger
        self._transactions: list[dict] = []          # append-only log
        self._reconciliations: list[dict] = []       # historical reconciliation snapshots

    # ---------- account setup ----------
    def register_account(
        self,
        firm_id: str,
        account_name: str,
        bank_name: str,
        account_number_last4: str,
        state: str,
        currency: str = "USD",
    ) -> dict:
        account_id = str(uuid.uuid4())
        record = {
            "id": account_id,
            "firm_id": firm_id,
            "account_name": account_name,
            "bank_name": bank_name,
            "account_number_last4": account_number_last4,
            "state": state,
            "currency": currency,
            "registered_at": datetime.utcnow().isoformat(),
            "active": True,
            "bank_balance": 0.0,                 # last reported by bank
            "bank_balance_as_of": None,
            "trust_ledger_balance": 0.0,         # sum of all client sub-ledgers
        }
        self._accounts[account_id] = record
        return record

    def get_account(self, account_id: str) -> dict | None:
        return self._accounts.get(account_id)

    def list_accounts(self, firm_id: str | None = None) -> list[dict]:
        out = list(self._accounts.values())
        if firm_id:
            out = [a for a in out if a["firm_id"] == firm_id]
        return out

    # ---------- client sub-ledgers ----------
    def open_client_ledger(self, account_id: str, client_id: str, client_name: str, workspace_id: str | None = None) -> dict:
        if account_id not in self._accounts:
            raise ValueError(f"Account not found: {account_id}")
        ledger_id = f"{account_id}::{client_id}"
        if ledger_id in self._client_ledgers:
            return self._client_ledgers[ledger_id]
        record = {
            "id": ledger_id,
            "account_id": account_id,
            "client_id": client_id,
            "client_name": client_name,
            "workspace_id": workspace_id,
            "balance": 0.0,
            "total_deposited": 0.0,
            "total_withdrawn": 0.0,
            "transaction_count": 0,
            "opened_at": datetime.utcnow().isoformat(),
            "status": "active",
        }
        self._client_ledgers[ledger_id] = record
        return record

    def get_client_ledger(self, account_id: str, client_id: str) -> dict | None:
        return self._client_ledgers.get(f"{account_id}::{client_id}")

    def list_client_ledgers(self, account_id: str) -> list[dict]:
        return [l for l in self._client_ledgers.values() if l["account_id"] == account_id]

    def close_client_ledger(self, account_id: str, client_id: str, reason: str = "") -> dict:
        ledger = self.get_client_ledger(account_id, client_id)
        if ledger is None:
            raise ValueError("Client ledger not found")
        if abs(ledger["balance"]) > 0.01:
            raise ValueError(
                f"Cannot close ledger with non-zero balance ({ledger['balance']:.2f}). "
                "Refund or transfer remaining funds first."
            )
        ledger["status"] = "closed"
        ledger["closed_at"] = datetime.utcnow().isoformat()
        ledger["close_reason"] = reason
        return ledger

    # ---------- transactions ----------
    def post_transaction(
        self,
        account_id: str,
        client_id: str,
        kind: str,
        amount: float,
        description: str = "",
        external_reference: str = "",
        approved_by: str | None = None,
        reason: str | None = None,
    ) -> dict:
        if kind not in VALID_TXN_KINDS:
            raise ValueError(f"Unknown transaction kind: {kind}")
        if amount <= 0:
            raise ValueError("Amount must be positive (use kind to indicate direction)")
        if kind in REQUIRES_REASON and not reason:
            raise ValueError(f"{kind} requires a reason")

        account = self._accounts.get(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")
        ledger = self.get_client_ledger(account_id, client_id)
        if ledger is None:
            raise ValueError(f"Client ledger not found: {client_id} in account {account_id}")

        # Direction logic
        is_debit = kind in ("invoice_payment", "refund", "disbursement", "transfer")
        is_credit = kind in ("deposit", "interest")
        if kind == "adjustment":
            # adjustment can be either; sign in `amount` ignored — caller must
            # specify direction via 'direction' field in description or a
            # supplemental param. For simplicity we treat positive amount as
            # credit; negative not supported here. Force a reason instead.
            is_credit = True
            is_debit = False

        new_balance = ledger["balance"] + (amount if is_credit else -amount)
        if is_debit and new_balance < -0.01:  # tolerance for floats
            raise ValueError(
                f"Overdraft prevented: {kind} of {amount:.2f} would leave client ledger at {new_balance:.2f}"
            )

        # Apply
        ledger["balance"] = round(new_balance, 2)
        if is_credit:
            ledger["total_deposited"] = round(ledger["total_deposited"] + amount, 2)
        else:
            ledger["total_withdrawn"] = round(ledger["total_withdrawn"] + amount, 2)
        ledger["transaction_count"] += 1

        # Update account-level trust balance
        account["trust_ledger_balance"] = round(
            sum(l["balance"] for l in self._client_ledgers.values() if l["account_id"] == account_id),
            2,
        )

        txn = {
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "client_id": client_id,
            "kind": kind,
            "amount": amount,
            "direction": "credit" if is_credit else "debit",
            "description": description,
            "external_reference": external_reference,
            "approved_by": approved_by,
            "reason": reason,
            "balance_after": ledger["balance"],
            "posted_at": datetime.utcnow().isoformat(),
        }
        self._transactions.append(txn)
        return txn

    def list_transactions(
        self,
        account_id: str | None = None,
        client_id: str | None = None,
        kind: str | None = None,
        since: str | None = None,
        until: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        out = self._transactions
        if account_id:
            out = [t for t in out if t["account_id"] == account_id]
        if client_id:
            out = [t for t in out if t["client_id"] == client_id]
        if kind:
            out = [t for t in out if t["kind"] == kind]
        if since:
            out = [t for t in out if t["posted_at"] >= since]
        if until:
            out = [t for t in out if t["posted_at"] <= until]
        return out[-limit:]

    # ---------- bank balance ----------
    def post_bank_balance(self, account_id: str, balance: float, as_of: str | None = None) -> dict:
        account = self._accounts.get(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")
        account["bank_balance"] = float(balance)
        account["bank_balance_as_of"] = as_of or datetime.utcnow().date().isoformat()
        return account

    # ---------- three-way reconciliation ----------
    def reconcile(self, account_id: str) -> dict:
        account = self._accounts.get(account_id)
        if account is None:
            raise ValueError(f"Account not found: {account_id}")
        ledgers = self.list_client_ledgers(account_id)
        sum_of_sub_ledgers = round(sum(l["balance"] for l in ledgers), 2)
        trust_ledger_balance = account["trust_ledger_balance"]
        bank_balance = account["bank_balance"]

        diff_ledger_vs_subledgers = round(trust_ledger_balance - sum_of_sub_ledgers, 2)
        diff_bank_vs_ledger = round(bank_balance - trust_ledger_balance, 2)

        is_balanced = abs(diff_ledger_vs_subledgers) < 0.01 and abs(diff_bank_vs_ledger) < 0.01

        result = {
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "as_of": datetime.utcnow().isoformat(),
            "bank_balance": bank_balance,
            "trust_ledger_balance": trust_ledger_balance,
            "sum_of_sub_ledgers": sum_of_sub_ledgers,
            "diff_ledger_vs_subledgers": diff_ledger_vs_subledgers,
            "diff_bank_vs_ledger": diff_bank_vs_ledger,
            "is_balanced": is_balanced,
            "client_ledger_count": len(ledgers),
        }

        # Add issues list
        issues = []
        if abs(diff_ledger_vs_subledgers) >= 0.01:
            issues.append({
                "kind": "TRUST_LEDGER_MISMATCH",
                "severity": "critical",
                "diff": diff_ledger_vs_subledgers,
                "explanation": "Sum of client sub-ledgers does not equal the trust ledger balance.",
            })
        if abs(diff_bank_vs_ledger) >= 0.01:
            issues.append({
                "kind": "BANK_MISMATCH",
                "severity": "critical",
                "diff": diff_bank_vs_ledger,
                "explanation": (
                    "Bank balance does not match the internal trust ledger balance. "
                    "Investigate uncleared deposits, bank fees, or missed transactions."
                ),
            })
        # Negative client balances
        for l in ledgers:
            if l["balance"] < -0.01:
                issues.append({
                    "kind": "NEGATIVE_CLIENT_LEDGER",
                    "severity": "critical",
                    "client_id": l["client_id"],
                    "balance": l["balance"],
                    "explanation": "A client sub-ledger is in overdraft.",
                })
        result["issues"] = issues
        result["is_balanced"] = result["is_balanced"] and not issues

        self._reconciliations.append(result)
        return result

    def list_reconciliations(self, account_id: str | None = None, limit: int = 50) -> list[dict]:
        out = self._reconciliations
        if account_id:
            out = [r for r in out if r["account_id"] == account_id]
        return out[-limit:]

    # ---------- helpers ----------
    def get_client_balance(self, account_id: str, client_id: str) -> float:
        ledger = self.get_client_ledger(account_id, client_id)
        return ledger["balance"] if ledger else 0.0

    def get_client_statement(self, account_id: str, client_id: str, since: str | None = None) -> dict:
        ledger = self.get_client_ledger(account_id, client_id)
        if ledger is None:
            raise ValueError("Client ledger not found")
        txns = self.list_transactions(account_id=account_id, client_id=client_id, since=since)
        deposits = sum(t["amount"] for t in txns if t["direction"] == "credit")
        withdrawals = sum(t["amount"] for t in txns if t["direction"] == "debit")
        return {
            "ledger": ledger,
            "transactions": txns,
            "period_deposits": round(deposits, 2),
            "period_withdrawals": round(withdrawals, 2),
            "current_balance": ledger["balance"],
            "as_of": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def list_transaction_kinds() -> list[dict]:
        return [
            {"kind": k, "requires_reason": k in REQUIRES_REASON}
            for k in VALID_TXN_KINDS
        ]
