import pytest
from fastapi.testclient import TestClient

from app import ledger
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_ledger():
    ledger.reset()
    ledger.open_account("alice")
    ledger.open_account("bob")
    ledger.deposit("alice", 10_000, "topup-1")


def test_transfer_moves_money_both_ways():
    res = client.post("/transfers", json={"from_account": "alice", "to_account": "bob", "amount_cents": 2_500, "reference": "t-1"})
    assert res.status_code == 201
    assert ledger.balance("alice") == 7_500
    assert ledger.balance("bob") == 2_500


def test_transfer_refuses_overdraft():
    res = client.post("/transfers", json={"from_account": "bob", "to_account": "alice", "amount_cents": 1, "reference": "t-2"})
    assert res.status_code == 400
    assert ledger.balance("bob") == 0


def test_reference_is_used_once():
    body = {"from_account": "alice", "to_account": "bob", "amount_cents": 100, "reference": "t-3"}
    assert client.post("/transfers", json=body).status_code == 201
    assert client.post("/transfers", json=body).status_code == 400
    assert ledger.balance("bob") == 100


def test_unknown_account_is_404():
    assert client.get("/accounts/carol").status_code == 404


def test_balance_endpoint():
    assert client.get("/accounts/alice").json() == {"id": "alice", "balance_cents": 10_000}
