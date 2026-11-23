"""Payout notifications: tell the customer when money leaves their wallet."""

import logging

log = logging.getLogger("ledgerly.notifications")


def payout_sent(account_id: str, iban: str, amount_cents: int, email: str) -> dict:
    """Builds the 'payout sent' email and records that it was sent."""
    subject = "Your payout is on its way"
    body = (
        f"We sent {amount_cents / 100:.2f} to your bank account {iban}. "
        "It usually arrives within one working day."
    )
    log.info("payout email to %s for account %s, iban %s, amount %s", email, account_id, iban, amount_cents)
    return {"to": email, "subject": subject, "body": body}


def payout_failed(account_id: str, iban: str, reason: str, email: str) -> dict:
    subject = "Your payout could not be sent"
    body = f"We could not send your payout to {iban}: {reason}. The money is back in your wallet."
    log.warning("payout failed for %s (%s): %s", account_id, iban, reason)
    return {"to": email, "subject": subject, "body": body}
