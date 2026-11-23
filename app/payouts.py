"""Payouts: send money from a wallet to the owner's bank account through the bank partner."""

import logging
import os
from decimal import ROUND_HALF_UP, Decimal

import requests

from app import ledger

log = logging.getLogger("ledgerly.payouts")

BANK_API_URL = "https://api.northbank-partner.example/v2/payouts"
PAYOUT_FEE_CENTS = 25


def _bank_api_key() -> str:
    key = os.environ.get("BANK_API_KEY")
    if not key:
        raise RuntimeError("BANK_API_KEY is not set")
    return key


def to_cents(amount: float) -> int:
    return int((Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def request_payout(account_id: str, amount: float, iban: str, reference: str) -> dict:
    """Pays `amount` (in the account currency, e.g. 12.50) out to `iban`, minus the fee."""
    amount_cents = to_cents(amount)
    if amount_cents <= PAYOUT_FEE_CENTS:
        raise ledger.LedgerError("payout must be larger than the fee")

    with ledger._lock:
        if ledger.get_account(account_id) is None:
            raise ledger.LedgerError("unknown account")
        if ledger.balance(account_id) < amount_cents:
            raise ledger.LedgerError("insufficient funds")
        # Record the debit first, so a timeout after the bank accepted can't pay out twice.
        ledger.get_account(account_id).entries.append(ledger._entry(account_id, -amount_cents, reference))

    log.info("payout %s: %s cents to iban ending %s", reference, amount_cents, iban[-4:])
    response = requests.post(
        BANK_API_URL,
        json={"iban": iban, "amount_cents": amount_cents - PAYOUT_FEE_CENTS, "reference": reference},
        headers={"Authorization": f"Bearer {_bank_api_key()}"},
        timeout=30,
    )
    response.raise_for_status()
    return {"reference": reference, "status": response.json().get("status", "submitted")}
