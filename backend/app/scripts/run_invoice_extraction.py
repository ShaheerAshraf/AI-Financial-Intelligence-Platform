"""
Run invoice OCR extraction for PENDING invoices.

From backend/:

    python -m app.scripts.run_invoice_extraction
    python -m app.scripts.run_invoice_extraction --limit 5
    python -m app.scripts.run_invoice_extraction --reset-pending
"""

import argparse

from app.db.database import SessionLocal
from app.models.invoice import Invoice
from app.services.invoice_extractor import (
    EXTRACTION_STATUS_PENDING,
    run_pending_extractions,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract structured invoice fields from raw OCR text."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of pending invoices to process.",
    )
    parser.add_argument(
        "--reset-pending",
        action="store_true",
        help="Mark all invoices as PENDING before running extraction.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset_pending:
            updated = (
                db.query(Invoice)
                .update(
                    {
                        Invoice.extraction_status: EXTRACTION_STATUS_PENDING,
                        Invoice.extraction_error: None,
                    },
                    synchronize_session=False,
                )
            )
            db.commit()
            print(f"Reset {updated} invoices to PENDING.")

        pending = (
            db.query(Invoice)
            .filter(Invoice.extraction_status == EXTRACTION_STATUS_PENDING)
            .count()
        )
        print(f"Pending invoices: {pending}")

        if pending == 0:
            return

        print("Running invoice extraction...")
        stats = run_pending_extractions(db, limit=args.limit)
        print(
            f"Done. processed={stats['processed']} "
            f"extracted={stats['extracted']} failed={stats['failed']}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
