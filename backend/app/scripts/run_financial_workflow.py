"""
Run the LangGraph financial intelligence workflow for a single transaction.

From backend/:

    python -m app.scripts.run_financial_workflow --transaction-id 716
    python -m app.scripts.run_financial_workflow --transaction-id 3028
"""

import argparse
import sys

from app.db.database import SessionLocal
from app.workflows.financial_workflow import run_financial_workflow


def _print_steps(steps: list[dict]) -> None:
    total = len(steps)
    for index, step in enumerate(steps, start=1):
        label = step.get("label", step.get("name", "Step"))
        status = step.get("status", "—")
        detail = step.get("detail")
        suffix = f" ({detail})" if detail else ""
        print(f"[{index}/{total}] {label} ... {status}{suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run LangGraph financial workflow for one transaction.",
    )
    parser.add_argument(
        "--transaction-id",
        type=int,
        required=True,
        help="Transaction ID to analyze through the full workflow.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print(f"Transaction: {args.transaction_id}\n")
        result = run_financial_workflow(db, args.transaction_id)
        steps = result.get("steps", [])
        if steps:
            _print_steps(steps)
        else:
            print("No steps recorded.")

        print()
        status = result.get("workflow_status", "UNKNOWN")
        if status == "NORMAL":
            print("Workflow completed — transaction is not suspicious (no agent pipeline run).")
        elif status == "COMPLETED":
            print("Workflow completed.")
            review = result.get("financial_review")
            if review:
                print(
                    f"Final risk: {review.get('risk_level')} · "
                    f"Decision: {review.get('decision')}"
                )
        elif status == "FAILED" or result.get("error"):
            print(f"Workflow failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
        else:
            print(f"Workflow status: {status}")
    except Exception as exc:
        db.rollback()
        print(f"Workflow error: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
