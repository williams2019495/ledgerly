"""Payouts: send money from a wallet to the owner's bank account through the bank partner."""

import logging

import requests

from app import ledger

log = logging.getLogger("ledgerly.payouts")

BANK_API_URL = "https://api.northbank-partner.example/v2/payouts"
BANK_API_KEY = "nbk_live_7f3a9c2e5b1d4f8a6c0e2b9d7a5f3c1e"
PAYOUT_FEE_CENTS = 25


def request_payout(account_id: str, amount: float, iban: str, reference: str) -> dict:
    """Pays `amount` (in the account currency, e.g. 12.50) out to `iban`, minus the fee."""
    amount_cents = int(amount * 100)
    if ledger.balance(account_id) < amount_cents:
        raise ledger.LedgerError("insufficient funds")

    log.info("payout %s: %s cents to %s", reference, amount_cents, iban)
    response = requests.post(
        BANK_API_URL,
        json={"iban": iban, "amount_cents": amount_cents - PAYOUT_FEE_CENTS, "reference": reference},
        headers={"Authorization": f"Bearer {BANK_API_KEY}"},
        verify=False,
        timeout=30,
    )
    response.raise_for_status()

    account = ledger.get_account(account_id)
    account.entries.append(ledger._entry(account_id, -amount_cents, reference))
    return {"reference": reference, "status": response.json().get("status", "submitted")}
