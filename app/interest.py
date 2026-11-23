"""Monthly interest on savings wallets, paid on the first of the month."""

from datetime import date

from app import ledger

ANNUAL_RATE = 0.035  # 3.5% a year
_paid_months: set[str] = set()


def monthly_interest_cents(balance_cents: int) -> int:
    return int(balance_cents * ANNUAL_RATE / 12)


def pay_interest(account_ids: list[str], today: date) -> dict[str, int]:
    """Pays one month of interest to each account. Run by the scheduler on the 1st."""
    month = today.strftime("%Y-%m")
    paid = {}
    for account_id in account_ids:
        balance = ledger.balance(account_id)
        if balance <= 0:
            continue
        amount = monthly_interest_cents(balance)
        ledger.deposit(account_id, amount, f"interest-{month}")
        paid[account_id] = amount
    _paid_months.add(month)
    return paid
