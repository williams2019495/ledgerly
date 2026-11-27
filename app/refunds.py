"""Refunds: send money back to a customer's wallet when a card payment is reversed."""

import logging
import threading

from app import ledger

log = logging.getLogger("ledgerly.refunds")

# payment_id -> the card payment we can refund against
_payments: dict[str, dict] = {}
_lock = threading.Lock()


class RefundError(Exception):
    def __init__(self, message: str, status: int):
        super().__init__(message)
        self.status = status


def reset() -> None:
    _payments.clear()


def record_payment(payment_id: str, account_id: str, amount_cents: int, iban: str) -> None:
    """Remembers a card payment so it can be refunded later."""
    _payments[payment_id] = {"account": account_id, "amount_cents": amount_cents, "iban": iban, "reversed": False, "refunded_cents": 0, "refunds": 0}


def mark_reversed(payment_id: str) -> None:
    """Called when the card provider reports the payment as reversed."""
    _payment(payment_id)["reversed"] = True


def mask_iban(iban: str) -> str:
    return "*" * max(0, len(iban) - 4) + iban[-4:]


def refund(payment_id: str, amount_cents: int, operator: str) -> dict:
    """Puts `amount_cents` back into the wallet that made a reversed payment, up to what was paid."""
    if amount_cents <= 0:
        raise RefundError("amount must be positive", 400)
    with _lock:
        payment = _payment(payment_id)
        if not payment["reversed"]:
            raise RefundError("payment has not been reversed", 409)
        remaining = payment["amount_cents"] - payment["refunded_cents"]
        if amount_cents > remaining:
            raise RefundError(f"only {remaining} cents left to refund", 409)
        payment["refunds"] += 1
        reference = f"refund-{payment_id}-{payment['refunds']}"
        ledger.deposit(payment["account"], amount_cents, reference)
        payment["refunded_cents"] += amount_cents
    log.info("refunded %d cents for %s to %s", amount_cents, payment_id, mask_iban(payment["iban"]))
    return {"payment_id": payment_id, "account": payment["account"], "amount_cents": amount_cents, "reference": reference}


def _payment(payment_id: str) -> dict:
    payment = _payments.get(payment_id)
    if payment is None:
        raise RefundError("unknown payment", 404)
    return payment
