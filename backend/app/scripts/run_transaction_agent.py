"""
Run Agent 1 against anomaly_results and save to transaction_analyses.

From backend/:

    python -m app.scripts.run_transaction_agent
    python -m app.scripts.run_transaction_agent --status HIGH --limit 5
"""

import argparse

from app.agents.persist import run_transaction_analyses
from app.db.database import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze anomalies with Gemini Agent 1 and save results."
    )
    parser.add_argument(
        "--status",
        default="HIGH",
        help="Anomaly status filter (default: HIGH). Use ALL for every anomaly.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of anomalies to process.",
    )
    args = parser.parse_args()

    status = None if args.status.upper() == "ALL" else args.status.upper()

    db = SessionLocal()
    try:
        print(
            f"Running transaction agent "
            f"(status={status or 'ALL'}, limit={args.limit})..."
        )
        saved = run_transaction_analyses(
            db,
            status=status,
            limit=args.limit,
        )
        print(f"Saved {saved} transaction analyses to PostgreSQL.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
