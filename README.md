# Ledgerly

A double-entry ledger service for wallets and payouts. Every transfer writes two entries that sum to zero, and a transfer reference can be used only once, so a retried request never moves money twice.

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest --cov=app
```

## Endpoints

| Method | Path | What it does |
|---|---|---|
| POST | `/accounts/{id}` | Open an account |
| GET | `/accounts/{id}` | Balance of an account |
| POST | `/transfers` | Move money between two accounts |
