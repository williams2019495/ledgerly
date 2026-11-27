import logging

import pytest
from fastapi.testclient import TestClient

from app import ledger, refunds
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-operator"}
IBAN = "DE89370400440532013000"


@pytest.fixture(autouse=True)
def reversed_payment(monkeypatch):
    monkeypatch.setenv("LEDGERLY_OPERATOR_TOKEN", "test-operator")
    ledger.reset()
    refunds.reset()
    ledger.open_account("alice")
    refunds.record_payment("pay-1", "alice", 2_500, IBAN)
    refunds.mark_reversed("pay-1")


def post(amount_cents, payment_id="pay-1", headers=AUTH):
    return client.post("/refunds", json={"payment_id": payment_id, "amount_cents": amount_cents}, headers=headers)


def test_full_refund_puts_money_back():
    assert post(2_500).status_code == 201
    assert ledger.balance("alice") == 2_500


def test_partial_refunds_up_to_the_payment():
    assert post(1_999).status_code == 201
    assert post(501).status_code == 201
    assert ledger.balance("alice") == 2_500


def test_cannot_refund_more_than_was_paid():
    assert post(2_501).status_code == 409
    assert ledger.balance("alice") == 0


def test_second_full_refund_is_rejected():
    assert post(2_500).status_code == 201
    assert post(2_500).status_code == 409
    assert ledger.balance("alice") == 2_500


def test_unknown_payment_is_404():
    assert post(100, payment_id="nope").status_code == 404


def test_payment_must_be_reversed_first():
    refunds.record_payment("pay-2", "alice", 1_000, IBAN)
    assert post(100, payment_id="pay-2").status_code == 409


def test_needs_the_operator_token():
    assert post(100, headers={}).status_code == 401
    assert post(100, headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_log_masks_the_iban(caplog):
    with caplog.at_level(logging.INFO, logger="ledgerly.refunds"):
        post(100)
    assert IBAN not in caplog.text
    assert "3000" in caplog.text
