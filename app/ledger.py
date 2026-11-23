"""In-memory double-entry ledger. Every transfer writes two entries that sum to zero."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import itertools
import threading


class LedgerError(Exception):
    pass


@dataclass
class Entry:
    id: int
    account_id: str
    amount_cents: int
    reference: str
    created_at: str


@dataclass
class Account:
    id: str
    entries: list[Entry] = field(default_factory=list)


_accounts: dict[str, Account] = {}
_references: set[str] = set()
_ids = itertools.count(1)
_lock = threading.Lock()


def reset() -> None:
    global _ids
    _accounts.clear()
    _references.clear()
    _ids = itertools.count(1)


def open_account(account_id: str) -> dict:
    if account_id in _accounts:
        raise LedgerError(f"account {account_id} already exists")
    _accounts[account_id] = Account(account_id)
    return {"id": account_id, "balance_cents": 0}


def get_account(account_id: str) -> Account | None:
    return _accounts.get(account_id)


def balance(account_id: str) -> int:
    account = _accounts[account_id]
    return sum(e.amount_cents for e in account.entries)


def deposit(account_id: str, amount_cents: int, reference: str) -> None:
    """Money arriving from outside the ledger (card top-up, bank transfer)."""
    if amount_cents <= 0:
        raise LedgerError("deposit must be positive")
    _accounts[account_id].entries.append(_entry(account_id, amount_cents, reference))


def transfer(from_id: str, to_id: str, amount_cents: int, reference: str) -> dict:
    """Moves money between two accounts. A reference can be used once, so a retried request is safe."""
    if from_id == to_id:
        raise LedgerError("cannot transfer to the same account")
    with _lock:
        if reference in _references:
            raise LedgerError(f"reference {reference} already used")
        source, target = _accounts.get(from_id), _accounts.get(to_id)
        if source is None or target is None:
            raise LedgerError("unknown account")
        if balance(from_id) < amount_cents:
            raise LedgerError("insufficient funds")
        source.entries.append(_entry(from_id, -amount_cents, reference))
        target.entries.append(_entry(to_id, amount_cents, reference))
        _references.add(reference)
    return {"reference": reference, "from": from_id, "to": to_id, "amount_cents": amount_cents}


def _entry(account_id: str, amount_cents: int, reference: str) -> Entry:
    return Entry(next(_ids), account_id, amount_cents, reference, datetime.now(timezone.utc).isoformat())
