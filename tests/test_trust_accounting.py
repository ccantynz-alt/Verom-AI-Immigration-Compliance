"""Tests for the IOLTA Trust Accounting service."""

from immigration_compliance.services.trust_accounting_service import (
    TrustAccountingService,
    VALID_TXN_KINDS,
    REQUIRES_REASON,
)


def _make_account():
    svc = TrustAccountingService()
    a = svc.register_account(firm_id="firm-1", account_name="IOLTA Trust", bank_name="Chase",
                             account_number_last4="1234", state="NY")
    return svc, a


def test_register_account():
    svc, a = _make_account()
    assert a["firm_id"] == "firm-1"
    assert a["currency"] == "USD"
    assert a["bank_balance"] == 0.0
    assert svc.get_account(a["id"]) == a


def test_open_client_ledger():
    svc, a = _make_account()
    l = svc.open_client_ledger(a["id"], "client-1", "Wei Chen", workspace_id="ws-1")
    assert l["client_name"] == "Wei Chen"
    assert l["balance"] == 0.0


def test_open_duplicate_ledger_returns_existing():
    svc, a = _make_account()
    l1 = svc.open_client_ledger(a["id"], "client-1", "Wei Chen")
    l2 = svc.open_client_ledger(a["id"], "client-1", "Wei Chen")
    assert l1["id"] == l2["id"]


def test_deposit_increases_client_balance():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    txn = svc.post_transaction(a["id"], "c1", "deposit", 5000)
    assert svc.get_client_balance(a["id"], "c1") == 5000.0
    assert txn["direction"] == "credit"


def test_invoice_payment_decreases_client_balance():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    svc.post_transaction(a["id"], "c1", "invoice_payment", 1500, description="Phase 1")
    assert svc.get_client_balance(a["id"], "c1") == 3500.0


def test_overdraft_prevented():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 1000)
    try:
        svc.post_transaction(a["id"], "c1", "invoice_payment", 2000)
        assert False
    except ValueError as e:
        assert "overdraft" in str(e).lower()


def test_disbursement_requires_reason():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    try:
        svc.post_transaction(a["id"], "c1", "disbursement", 1710)
        assert False
    except ValueError:
        pass
    # With reason: succeeds
    txn = svc.post_transaction(a["id"], "c1", "disbursement", 1710, reason="USCIS filing fee")
    assert txn["reason"] == "USCIS filing fee"


def test_refund_requires_reason():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    try:
        svc.post_transaction(a["id"], "c1", "refund", 1000)
        assert False
    except ValueError:
        pass


def test_unknown_transaction_kind_rejected():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    try:
        svc.post_transaction(a["id"], "c1", "fake_kind", 100)
        assert False
    except ValueError:
        pass


def test_negative_amount_rejected():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    try:
        svc.post_transaction(a["id"], "c1", "deposit", -100)
        assert False
    except ValueError:
        pass


def test_reconciliation_balanced():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.open_client_ledger(a["id"], "c2", "Client Two")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    svc.post_transaction(a["id"], "c2", "deposit", 3000)
    svc.post_bank_balance(a["id"], 8000)
    recon = svc.reconcile(a["id"])
    assert recon["is_balanced"] is True
    assert len(recon["issues"]) == 0


def test_reconciliation_bank_mismatch():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    svc.post_bank_balance(a["id"], 4000)  # mismatch
    recon = svc.reconcile(a["id"])
    assert recon["is_balanced"] is False
    assert any(i["kind"] == "BANK_MISMATCH" for i in recon["issues"])


def test_close_ledger_with_balance_blocked():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    try:
        svc.close_client_ledger(a["id"], "c1", reason="case dropped")
        assert False
    except ValueError as e:
        assert "non-zero" in str(e).lower()


def test_close_ledger_with_zero_balance():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 1000)
    svc.post_transaction(a["id"], "c1", "refund", 1000, reason="case dropped")
    closed = svc.close_client_ledger(a["id"], "c1", reason="case dropped")
    assert closed["status"] == "closed"


def test_client_statement():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    svc.post_transaction(a["id"], "c1", "invoice_payment", 1500)
    stmt = svc.get_client_statement(a["id"], "c1")
    assert stmt["current_balance"] == 3500.0
    assert stmt["period_deposits"] == 5000.0
    assert stmt["period_withdrawals"] == 1500.0
    assert len(stmt["transactions"]) == 2


def test_account_trust_balance_aggregates_sub_ledgers():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.open_client_ledger(a["id"], "c2", "Client Two")
    svc.post_transaction(a["id"], "c1", "deposit", 5000)
    svc.post_transaction(a["id"], "c2", "deposit", 2500)
    refreshed = svc.get_account(a["id"])
    assert refreshed["trust_ledger_balance"] == 7500.0


def test_list_transactions_filters():
    svc, a = _make_account()
    svc.open_client_ledger(a["id"], "c1", "Client One")
    svc.open_client_ledger(a["id"], "c2", "Client Two")
    svc.post_transaction(a["id"], "c1", "deposit", 1000)
    svc.post_transaction(a["id"], "c2", "deposit", 2000)
    c1_only = svc.list_transactions(account_id=a["id"], client_id="c1")
    assert len(c1_only) == 1
    deposits_only = svc.list_transactions(account_id=a["id"], kind="deposit")
    assert len(deposits_only) == 2


def test_negative_balance_flagged_in_reconciliation():
    """A bug in postings shouldn't allow this normally, but test the
    reconciliation surfaces it as an issue if it ever happens."""
    svc, a = _make_account()
    l = svc.open_client_ledger(a["id"], "c1", "Client One")
    # Manually corrupt for test
    l["balance"] = -100
    svc.post_bank_balance(a["id"], -100)
    recon = svc.reconcile(a["id"])
    assert any(i["kind"] == "NEGATIVE_CLIENT_LEDGER" for i in recon["issues"])


def test_transaction_kinds_listing():
    kinds = TrustAccountingService.list_transaction_kinds()
    kind_ids = {k["kind"] for k in kinds}
    assert kind_ids == set(VALID_TXN_KINDS)


def test_requires_reason_constant():
    assert "adjustment" in REQUIRES_REASON
    assert "refund" in REQUIRES_REASON
    assert "disbursement" in REQUIRES_REASON
    assert "deposit" not in REQUIRES_REASON
