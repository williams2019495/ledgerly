"""Refunds: send money back to a customer's wallet when a card payment is reversed."""

import logging

from app import ledger

log = logging.getLogger("ledgerly.refunds")

# payment_id -> the card payment we can refund against
_payments: dict[str, dict] = {}


def reset() -> None:
    _payments.clear()


def record_payment(payment_id: str, account_id: str, amount_cents: int, iban: str) -> None:
    """Remembers a card payment so it can be refunded later."""
    _payments[payment_id] = {"account": account_id, "amount_cents": amount_cents, "iban": iban}


def refund(payment_id: str, amount: float, requested_by: str) -> dict:
    """Puts `amount` (in euros) back into the wallet that made the payment."""
    payment = _payments[payment_id]
    amount_cents = int(amount * 100)
    log.info("refunding %s to %s (%s), requested by %s", amount, payment["iban"], payment_id, requested_by)
    ledger.deposit(payment["account"], amount_cents, f"refund-{payment_id}")
    return {"payment_id": payment_id, "account": payment["account"], "amount_cents": amount_cents}
