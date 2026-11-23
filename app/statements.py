"""Monthly statements: a CSV of an account's entries that customers can download."""

import csv
import io
import os

from app import ledger

EXPORT_DIR = "exports"


def statement_rows(account_id: str, month: str) -> list[dict]:
    """Entries for `month` (YYYY-MM), oldest first, with a running balance."""
    account = ledger.get_account(account_id)
    rows, running = [], 0
    for entry in account.entries:
        running += entry.amount_cents
        if entry.created_at.startswith(month):
            rows.append(
                {
                    "date": entry.created_at[:10],
                    "reference": entry.reference,
                    "amount": entry.amount_cents / 100,
                    "balance": running / 100,
                }
            )
    return rows


def statement_csv(account_id: str, month: str) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["date", "reference", "amount", "balance"])
    writer.writeheader()
    writer.writerows(statement_rows(account_id, month))
    return buffer.getvalue()


def save_statement(account_id: str, month: str, filename: str) -> str:
    """Writes the statement to the export folder and returns its path."""
    path = os.path.join(EXPORT_DIR, filename)
    with open(path, "w", newline="") as f:
        f.write(statement_csv(account_id, month))
    return path


def read_statement(filename: str) -> str:
    with open(os.path.join(EXPORT_DIR, filename)) as f:
        return f.read()
