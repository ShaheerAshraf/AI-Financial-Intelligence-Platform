import sys
from pathlib import Path

import pandas as pd

# Add backend to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.models.transaction import Transaction


def load_transactions() -> pd.DataFrame:
    db = SessionLocal()

    try:
        transactions = db.query(Transaction).all()

        data = [
            {
                "id": transaction.id,
                "company_id": transaction.company_id,
                "vendor_id": transaction.vendor_id,
                "category_id": transaction.category_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "transaction_date": transaction.transaction_date,
                "description": transaction.description,
            }
            for transaction in transactions
        ]

        return pd.DataFrame(data)

    finally:
        db.close()