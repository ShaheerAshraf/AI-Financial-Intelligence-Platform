"""
Seed realistic OCR-extracted invoice records linked to transactions.

Includes matching cases and deliberate mismatches for Agent 2 testing.

From backend/:

    python -m app.scripts.seed_invoices
    python -m app.scripts.seed_invoices --force
"""

import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db.database import SessionLocal
from app.models.anomaly_result import AnomalyResult
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.vendor import Vendor

random.seed(42)


def format_eur(amount: Decimal | float) -> str:
    value = float(amount)
    return f"EUR {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_date_de(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def build_raw_ocr_text(
    *,
    vendor_name: str,
    invoice_number: str,
    invoice_date: date,
    due_date: date,
    amount: Decimal,
    currency: str,
    description: str,
) -> str:
    return f"""{vendor_name}
Invoice No: {invoice_number}
Date: {format_date_de(invoice_date)}
Due Date: {format_date_de(due_date)}

Description:
{description}

Subtotal: {format_eur(amount)}
VAT (0%): EUR 0,00
Total: {format_eur(amount)}
Currency: {currency}

Payment terms: Net 30
Thank you for your business.
""".strip()


def build_invoice(
    transaction: Transaction,
    vendor_name: str,
    *,
    amount: Decimal,
    invoice_date: date,
    due_date: date,
    invoice_number: str,
    description: str,
    ocr_confidence: float,
) -> Invoice:
    currency = transaction.currency or "EUR"
    raw_ocr_text = build_raw_ocr_text(
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        amount=amount,
        currency=currency,
        description=description,
    )
    return Invoice(
        transaction_id=transaction.id,
        invoice_number=invoice_number,
        vendor_name=vendor_name,
        invoice_date=invoice_date,
        due_date=due_date,
        amount=amount,
        currency=currency,
        description=description,
        raw_ocr_text=raw_ocr_text,
        ocr_confidence=ocr_confidence,
    )


def matching_invoice(transaction: Transaction, vendor_name: str) -> Invoice:
    due = transaction.transaction_date + timedelta(days=30)
    return build_invoice(
        transaction,
        vendor_name,
        amount=transaction.amount,
        invoice_date=transaction.transaction_date,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}",
        description=transaction.description or "Professional services",
        ocr_confidence=round(random.uniform(0.91, 0.99), 2),
    )


def amount_mismatch_invoice(transaction: Transaction, vendor_name: str) -> Invoice:
    """Invoice total differs from transaction amount."""
    inflated = (transaction.amount * Decimal("0.90")).quantize(Decimal("0.01"))
    due = transaction.transaction_date + timedelta(days=30)
    return build_invoice(
        transaction,
        vendor_name,
        amount=inflated,
        invoice_date=transaction.transaction_date,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}-A",
        description=transaction.description or "Professional services",
        ocr_confidence=round(random.uniform(0.88, 0.96), 2),
    )


def vendor_mismatch_invoice(transaction: Transaction) -> Invoice:
    """Invoice vendor name does not match transaction vendor."""
    wrong_vendor = "ACME Consulting GmbH"
    due = transaction.transaction_date + timedelta(days=30)
    return build_invoice(
        transaction,
        wrong_vendor,
        amount=transaction.amount,
        invoice_date=transaction.transaction_date,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}-V",
        description=transaction.description or "Consulting services",
        ocr_confidence=round(random.uniform(0.82, 0.93), 2),
    )


def date_mismatch_invoice(transaction: Transaction, vendor_name: str) -> Invoice:
    """Invoice date differs from transaction date."""
    shifted = transaction.transaction_date - timedelta(days=14)
    due = shifted + timedelta(days=30)
    return build_invoice(
        transaction,
        vendor_name,
        amount=transaction.amount,
        invoice_date=shifted,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}-D",
        description=transaction.description or "Professional services",
        ocr_confidence=round(random.uniform(0.86, 0.95), 2),
    )


def multiple_mismatch_invoice(transaction: Transaction) -> Invoice:
    """Amount, vendor, and date all differ."""
    wrong_vendor = "Global Supplies Ltd"
    wrong_amount = (transaction.amount - Decimal("10000")).quantize(Decimal("0.01"))
    wrong_date = transaction.transaction_date + timedelta(days=21)
    due = wrong_date + timedelta(days=30)
    return build_invoice(
        transaction,
        wrong_vendor,
        amount=wrong_amount,
        invoice_date=wrong_date,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}-M",
        description="Bulk equipment order",
        ocr_confidence=round(random.uniform(0.79, 0.89), 2),
    )


def low_confidence_match_invoice(transaction: Transaction, vendor_name: str) -> Invoice:
    """Structured fields match, but OCR confidence is low."""
    due = transaction.transaction_date + timedelta(days=30)
    invoice = build_invoice(
        transaction,
        vendor_name,
        amount=transaction.amount,
        invoice_date=transaction.transaction_date,
        due_date=due,
        invoice_number=f"INV-{transaction.id:06d}-L",
        description=transaction.description or "Scanned invoice — poor quality",
        ocr_confidence=round(random.uniform(0.48, 0.58), 2),
    )
    invoice.raw_ocr_text = (
        invoice.raw_ocr_text
        + "\n\n[OCR NOTE: faint scan, partial table overlap, low image quality]"
    )
    return invoice


def load_transactions(db) -> list[tuple[Transaction, str]]:
    rows = (
        db.query(Transaction, Vendor.name)
        .outerjoin(Vendor, Vendor.id == Transaction.vendor_id)
        .options(joinedload(Transaction.anomaly_results))
        .order_by(Transaction.id.asc())
        .all()
    )
    return [(txn, vendor_name or "Unknown Vendor") for txn, vendor_name in rows]


def load_high_risk_ids(db) -> set[int]:
    ids = db.scalars(
        select(AnomalyResult.transaction_id).where(
            AnomalyResult.status == "HIGH"
        )
    ).all()
    return set(ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OCR invoice records.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing invoices and re-seed.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(Invoice).count()
        if existing and not args.force:
            print(f"Found {existing} invoices. Skipping (use --force to re-seed).")
            return

        if existing and args.force:
            deleted = db.query(Invoice).delete(synchronize_session=False)
            db.commit()
            print(f"Deleted {deleted} existing invoices.")

        transactions = load_transactions(db)
        if not transactions:
            print("No transactions found. Run seed_data and ML pipeline first.")
            return

        high_risk_ids = load_high_risk_ids(db)
        high_risk = [(t, v) for t, v in transactions if t.id in high_risk_ids]
        normal = [(t, v) for t, v in transactions if t.id not in high_risk_ids]

        random.shuffle(normal)
        random.shuffle(high_risk)

        invoices: list[Invoice] = []
        used_ids: set[int] = set()

        def take(pool: list[tuple[Transaction, str]], n: int) -> list[tuple[Transaction, str]]:
            picked = []
            for item in pool:
                if item[0].id in used_ids:
                    continue
                picked.append(item)
                used_ids.add(item[0].id)
                if len(picked) >= n:
                    break
            return picked

        # Matching normal transactions
        for txn, vendor_name in take(normal, 20):
            invoices.append(matching_invoice(txn, vendor_name))

        # Matching high-risk (control group — invoice aligns)
        for txn, vendor_name in take(high_risk, 5):
            invoices.append(matching_invoice(txn, vendor_name))

        # Amount mismatches on high-risk anomalies
        for txn, vendor_name in take(high_risk, 8):
            invoices.append(amount_mismatch_invoice(txn, vendor_name))

        # Vendor mismatches
        for txn, _ in take(high_risk + normal, 5):
            invoices.append(vendor_mismatch_invoice(txn))

        # Date mismatches
        for txn, vendor_name in take(normal, 5):
            invoices.append(date_mismatch_invoice(txn, vendor_name))

        # Multiple mismatches on high-risk
        for txn, _ in take(high_risk, 6):
            invoices.append(multiple_mismatch_invoice(txn))

        # Low OCR confidence but structurally matching
        for txn, vendor_name in take(normal, 4):
            invoices.append(low_confidence_match_invoice(txn, vendor_name))

        db.add_all(invoices)
        db.commit()

        match_count = 20 + 5 + 4
        mismatch_count = len(invoices) - match_count
        print(f"Created {len(invoices)} invoice records.")
        print(f"  ~{match_count} matching / low-confidence-match cases")
        print(f"  ~{mismatch_count} deliberate mismatch cases")
        print(f"  Linked to {len(used_ids)} unique transactions")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
