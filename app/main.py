"""Ledgerly: a double-entry ledger service for wallets and payouts."""

import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from app import ledger, refunds

app = FastAPI(title="Ledgerly")


class TransferIn(BaseModel):
    from_account: str
    to_account: str
    amount_cents: int = Field(gt=0)
    reference: str = Field(min_length=1, max_length=64)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/accounts/{account_id}")
def open_account(account_id: str):
    try:
        return ledger.open_account(account_id)
    except ledger.LedgerError as err:
        raise HTTPException(status_code=409, detail=str(err))


@app.get("/accounts/{account_id}")
def get_account(account_id: str):
    account = ledger.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": account_id, "balance_cents": ledger.balance(account_id)}


@app.post("/transfers", status_code=201)
def transfer(body: TransferIn):
    try:
        return ledger.transfer(body.from_account, body.to_account, body.amount_cents, body.reference)
    except ledger.LedgerError as err:
        raise HTTPException(status_code=400, detail=str(err))


class RefundIn(BaseModel):
    payment_id: str
    amount_cents: int = Field(gt=0)
    request_id: str = Field(min_length=1, max_length=64)


class PaymentIn(BaseModel):
    payment_id: str = Field(min_length=1, max_length=64)
    account_id: str
    amount_cents: int = Field(gt=0)
    iban: str = Field(min_length=5, max_length=34)


def require_operator(authorization: str = Header(default="")) -> str:
    """Refunds are for support staff only: they send the operator token from LEDGERLY_OPERATOR_TOKEN."""
    expected = os.environ.get("LEDGERLY_OPERATOR_TOKEN", "")
    given = authorization.removeprefix("Bearer ")
    if not expected or not secrets.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="operator token required")
    return "operator"


@app.post("/payments", status_code=201)
def record_payment(body: PaymentIn, operator: str = Depends(require_operator)):
    """The card provider's capture, recorded so it can be refunded later."""
    refunds.record_payment(body.payment_id, body.account_id, body.amount_cents, body.iban)
    return {"payment_id": body.payment_id}


@app.post("/payments/{payment_id}/reversed")
def payment_reversed(payment_id: str, operator: str = Depends(require_operator)):
    try:
        refunds.mark_reversed(payment_id)
    except refunds.RefundError as err:
        raise HTTPException(status_code=err.status, detail=str(err))
    return {"payment_id": payment_id, "reversed": True}


@app.post("/refunds", status_code=201)
def refund(body: RefundIn, operator: str = Depends(require_operator)):
    try:
        return refunds.refund(body.payment_id, body.amount_cents, operator, body.request_id)
    except refunds.RefundError as err:
        raise HTTPException(status_code=err.status, detail=str(err))
