"""
Run Agent 2 (Invoice Verification) against extracted invoices.

From backend/:

    python -m app.scripts.run_invoice_agent
    python -m app.scripts.run_invoice_agent --limit 5
    python -m app.scripts.run_invoice_agent --force
"""

import argparse

from app.agents.invoice_agent import AGENT_VERSION
from app.agents.invoice_verification_runner import run_invoice_verifications
from app.db.database import SessionLocal
from app.models.invoice_verification import InvoiceVerification


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify extracted invoices against transactions (Agent 2)."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of unverified invoices to process.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing verifications for this agent version before running.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.force:
            deleted = (
                db.query(InvoiceVerification)
                .filter(InvoiceVerification.agent_version == AGENT_VERSION)
                .delete(synchronize_session=False)
            )
            db.commit()
            print(f"Deleted {deleted} existing verifications ({AGENT_VERSION}).")

        print("Running invoice verification agent...")
        stats = run_invoice_verifications(db, limit=args.limit)
        print(
            f"Done. pending={stats['pending']} "
            f"verified={stats['verified']} failed={stats['failed']}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
