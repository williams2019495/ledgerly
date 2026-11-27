from fastapi.testclient import TestClient

from app import ledger, refunds
from app.main import app

client = TestClient(app)


def test_refund_puts_money_back():
    ledger.reset()
    refunds.reset()
    ledger.open_account("alice")
    refunds.record_payment("pay-1", "alice", 2_500, "DE89370400440532013000")
    res = client.post("/refunds", json={"payment_id": "pay-1", "amount": 25, "requested_by": "alice"})
    assert res.status_code == 201
    assert ledger.balance("alice") == 2_500
