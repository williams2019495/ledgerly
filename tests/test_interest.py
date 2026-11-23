from datetime import date

from app import interest, ledger


def setup_function():
    ledger.reset()
    ledger.open_account("saver")
    ledger.deposit("saver", 120_000, "topup")


def test_pays_one_month_of_interest():
    paid = interest.pay_interest(["saver"], date(2026, 12, 1))
    assert paid == {"saver": 350}
    assert ledger.balance("saver") == 120_350
