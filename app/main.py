"""Ledgerly: a double-entry ledger service for wallets and payouts."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app import ledger, statements

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


@app.get("/accounts/{account_id}/statements/{month}", response_class=PlainTextResponse)
def statement(account_id: str, month: str):
    if ledger.get_account(account_id) is None:
        raise HTTPException(status_code=404, detail="not found")
    return statements.statement_csv(account_id, month)


@app.post("/accounts/{account_id}/statements/{month}/save")
def save_statement(account_id: str, month: str, filename: str):
    return {"path": statements.save_statement(account_id, month, filename)}


@app.get("/statements/{filename}", response_class=PlainTextResponse)
def download_statement(filename: str):
    return statements.read_statement(filename)
