"""
Run Agent 3 (Financial Review) against completed Agent 1 + Agent 2 outputs.

From backend/:

    python -m app.scripts.run_financial_review_agent
    python -m app.scripts.run_financial_review_agent --limit 5
    python -m app.scripts.run_financial_review_agent --force
"""

import argparse

from app.agents.financial_review_runner import run_financial_reviews
from app.agents.review_agent import AGENT_VERSION
from app.db.database import SessionLocal
from app.models.financial_review import FinancialReview


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run final financial review (Agent 3) on completed pipeline data."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of unreviewed transactions to process.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing reviews for this agent version before running.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.force:
            deleted = (
                db.query(FinancialReview)
                .filter(FinancialReview.agent_version == AGENT_VERSION)
                .delete(synchronize_session=False)
            )
            db.commit()
            print(f"Deleted {deleted} existing reviews ({AGENT_VERSION}).")

        print("Running financial review agent...")
        stats = run_financial_reviews(db, limit=args.limit)
        print(
            f"Done. pending={stats['pending']} "
            f"reviewed={stats['reviewed']} failed={stats['failed']}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
