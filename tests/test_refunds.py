import logging
import threading

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


_ids = iter(range(1, 10_000))


def post(amount_cents, payment_id="pay-1", headers=AUTH, request_id=None):
    body = {"payment_id": payment_id, "amount_cents": amount_cents, "request_id": request_id or f"r-{next(_ids)}"}
    return client.post("/refunds", json=body, headers=headers)


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


def test_retry_with_the_same_request_id_pays_once():
    assert post(1_000, request_id="retry-1").status_code == 201
    assert post(1_000, request_id="retry-1").status_code == 201
    assert ledger.balance("alice") == 1_000


def test_partials_cannot_add_up_past_the_payment():
    assert post(2_000).status_code == 201
    assert post(501).status_code == 409
    assert ledger.balance("alice") == 2_000


def test_zero_negative_and_fractional_amounts_are_rejected():
    for amount in (0, -100, 10.5):
        assert post(amount).status_code == 422
    assert ledger.balance("alice") == 0


def test_unset_operator_token_refuses_everyone(monkeypatch):
    monkeypatch.delenv("LEDGERLY_OPERATOR_TOKEN")
    assert post(100).status_code == 401


def test_non_ascii_token_is_401_not_500():
    assert post(100, headers={"Authorization": "Bearer tést"}).status_code == 401


def test_concurrent_refunds_never_exceed_the_payment():
    results = []
    threads = [threading.Thread(target=lambda: results.append(post(1_000).status_code)) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(201) == 2
    assert ledger.balance("alice") == 2_000


def test_payments_are_recorded_and_reversed_through_the_api():
    res = client.post("/payments", json={"payment_id": "pay-9", "account_id": "alice", "amount_cents": 700, "iban": IBAN}, headers=AUTH)
    assert res.status_code == 201
    assert client.post("/payments/pay-9/reversed", headers=AUTH).status_code == 200
    assert post(700, payment_id="pay-9").status_code == 201
    assert client.post("/payments/nope/reversed", headers=AUTH).status_code == 404
