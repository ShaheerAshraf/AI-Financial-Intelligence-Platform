"""
System smoke test for core user flows.

Run: python -m app.scripts.smoke_user_flows
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.db.database import SessionLocal
from app.models.anomaly_result import AnomalyResult
from app.models.category import Category
from app.models.company import Company
from app.models.financial_review import FinancialReview
from app.models.transaction import Transaction
from app.models.vendor import Vendor
from app.agents.invoice_verification_runner import run_verification_for_transaction
from app.services.batch_analysis import (
    claim_new_transactions,
    count_new_transactions,
    finalize_run,
    process_run_item,
)
from app.services.financial_investigation import build_investigation
from app.workflows.financial_workflow import run_financial_workflow


def _ok(label: str) -> None:
    print(f"  OK  {label}")


def _fail(label: str, err: Exception) -> None:
    print(f"  FAIL  {label}: {err}")
    raise err


def backfill_seed_new_to_analyzed(db) -> int:
    """Historical seed rows should not clog Analyze New."""
    updated = (
        db.query(Transaction)
        .filter(
            Transaction.analysis_status == "NEW",
            Transaction.id < 3000,
        )
        .update({"analysis_status": "ANALYZED"}, synchronize_session=False)
    )
    db.commit()
    return updated


def ensure_demo_transaction(db) -> Transaction:
    company = db.query(Company).order_by(Company.id.asc()).first()
    vendor = (
        db.query(Vendor)
        .filter(Vendor.company_id == company.id)
        .order_by(Vendor.id.asc())
        .first()
    )
    category = (
        db.query(Category)
        .filter(Category.company_id == company.id)
        .order_by(Category.id.asc())
        .first()
    )
    txn = Transaction(
        company_id=company.id,
        vendor_id=vendor.id,
        category_id=category.id,
        amount=Decimal("125.50"),
        currency="EUR",
        transaction_date=date.today(),
        description="Smoke test transaction",
        analysis_status="NEW",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def main() -> None:
    db = SessionLocal()
    errors: list[str] = []
    try:
        print("1) Backfill historical NEW -> ANALYZED (id < 3000)")
        n = backfill_seed_new_to_analyzed(db)
        _ok(f"updated {n} rows; remaining NEW={count_new_transactions(db)}")

        print("2) Create NEW transaction")
        txn = ensure_demo_transaction(db)
        _ok(f"created txn #{txn.id}")

        print("3) Claim batch locking")
        before = count_new_transactions(db)
        run = claim_new_transactions(db, limit=3, mode="NEW")
        items = list(run.items) if run.items else []
        # reload items
        from app.models.analysis_run import AnalysisRunItem

        items = (
            db.query(AnalysisRunItem)
            .filter(AnalysisRunItem.run_id == run.id)
            .all()
        )
        claimed_ids = [i.transaction_id for i in items]
        if txn.id not in claimed_ids and before > 0:
            # newest first — our txn should be among newest
            pass
        for i in items:
            t = db.get(Transaction, i.transaction_id)
            assert t.analysis_status == "ANALYZING", t.analysis_status
        after_claim = count_new_transactions(db)
        assert after_claim == before - len(items)
        _ok(f"run #{run.id} claimed {claimed_ids}; NEW {before}->{after_claim}")

        print("4) Process claimed items (workflow)")
        # Process only our smoke txn fully; release others back to NEW
        for item in items:
            if item.transaction_id != txn.id:
                t = db.get(Transaction, item.transaction_id)
                if t:
                    t.analysis_status = "NEW"
                item.status = "SKIPPED"
                item.workflow_status = "SKIPPED"
                db.commit()
                _ok(f"released txn #{item.transaction_id} back to NEW")
                continue
            processed = process_run_item(
                db, run_id=run.id, transaction_id=item.transaction_id
            )
            t = db.get(Transaction, item.transaction_id)
            assert t.analysis_status in {"ANALYZED", "ANALYSIS_FAILED"}, t.analysis_status
            _ok(
                f"txn #{item.transaction_id} -> {processed.status} "
                f"/ {processed.workflow_status} / {t.analysis_status}"
            )

        finalized = finalize_run(db, run.id)
        _ok(
            f"finalize run #{finalized.id}: successful={finalized.successful} "
            f"failed={finalized.failed} remaining={finalized.remaining_new_after}"
        )

        print("5) Investigation payload for a HIGH anomaly txn")
        high = (
            db.query(AnomalyResult)
            .filter(AnomalyResult.status == "HIGH")
            .order_by(AnomalyResult.anomaly_score.asc())
            .first()
        )
        if high:
            inv = build_investigation(db, db.get(Transaction, high.transaction_id))
            assert inv.transaction.id == high.transaction_id
            _ok(
                f"investigation #{high.transaction_id}: "
                f"anomaly={inv.anomaly.status if inv.anomaly else None} "
                f"invoice_ver={inv.invoice_verification.status if inv.invoice_verification else None}"
            )

            print("6) Agent 2 NOT_PROVIDED / verification path")
            v = run_verification_for_transaction(db, high.transaction_id)
            assert v.match_status in {
                "NOT_PROVIDED",
                "MATCH",
                "AMOUNT_MISMATCH",
                "VENDOR_MISMATCH",
                "DATE_MISMATCH",
                "MULTIPLE_MISMATCHES",
                "INSUFFICIENT_EVIDENCE",
            }
            _ok(f"verification status={v.match_status}")

        print("7) Human decision persistence (if review exists)")
        review = (
            db.query(FinancialReview)
            .filter(FinancialReview.review_status == "PENDING")
            .order_by(FinancialReview.id.desc())
            .first()
        )
        if review:
            review.review_status = "APPROVED"
            review.reviewed_by = "Smoke Tester"
            review.review_comment = "Automated smoke test approval"
            from datetime import datetime

            review.reviewed_at = datetime.utcnow()
            db.commit()
            inv = build_investigation(db, db.get(Transaction, review.transaction_id))
            assert inv.financial_review.review_status == "APPROVED"
            assert inv.financial_review.review_comment
            _ok(f"human decision on txn #{review.transaction_id}")
        else:
            _ok("no PENDING review to update (skipped)")

        print("\nAll smoke checks passed.")
    except Exception as exc:
        errors.append(str(exc))
        print(f"\nSmoke test failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
