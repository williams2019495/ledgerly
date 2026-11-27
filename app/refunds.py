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
    """Remembers a card payment so it can be refunded later. A payment is recorded once."""
    if payment_id in _payments:
        raise RefundError("payment already recorded", 409)
    if ledger.get_account(account_id) is None:
        raise RefundError("unknown account", 404)
    _payments[payment_id] = {"account": account_id, "amount_cents": amount_cents, "iban": iban, "reversed": False, "refunded_cents": 0, "by_request": {}}


def mark_reversed(payment_id: str) -> None:
    """Called when the card provider reports the payment as reversed."""
    _payment(payment_id)["reversed"] = True


def mask_iban(iban: str) -> str:
    return "*" * max(0, len(iban) - 4) + iban[-4:]


def refund(payment_id: str, amount_cents: int, operator: str, request_id: str) -> dict:
    """Puts `amount_cents` back into the wallet that made a reversed payment, up to what was paid.

    `request_id` comes from the caller and makes a retry safe: the same id never pays out twice."""
    if amount_cents <= 0:
        raise RefundError("amount must be positive", 400)
    with _lock:
        payment = _payment(payment_id)
        done = payment["by_request"].get(request_id)
        if done is not None:
            if done["amount_cents"] != amount_cents:
                raise RefundError("request_id already used for a different amount", 409)
            return done
        if not payment["reversed"]:
            raise RefundError("payment has not been reversed", 409)
        remaining = payment["amount_cents"] - payment["refunded_cents"]
        if amount_cents > remaining:
            raise RefundError(f"only {remaining} cents left to refund", 409)
        reference = f"refund-{payment_id}-{request_id}"
        ledger.deposit(payment["account"], amount_cents, reference)
        payment["refunded_cents"] += amount_cents
        result = {"payment_id": payment_id, "account": payment["account"], "amount_cents": amount_cents, "reference": reference}
        payment["by_request"][request_id] = result
    log.info("refunded %d cents for %s to %s, by %s", amount_cents, payment_id, mask_iban(payment["iban"]), operator)
    return result


def _payment(payment_id: str) -> dict:
    payment = _payments.get(payment_id)
    if payment is None:
        raise RefundError("unknown payment", 404)
    return payment
