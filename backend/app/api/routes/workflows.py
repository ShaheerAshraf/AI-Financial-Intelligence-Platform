from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.analysis_run import AnalysisRun, AnalysisRunItem
from app.models.transaction import Transaction
from app.schemas.workflow import (
    AnalysisRunItemResponse,
    AnalysisRunResponse,
    BatchWorkflowItem,
    BatchWorkflowResponse,
    ClaimBatchResponse,
    PaginatedAnalysisRunsResponse,
    ProcessItemResponse,
    WorkflowRunResponse,
    WorkflowStepResult,
)
from app.services.batch_analysis import (
    STATUS_ANALYZING,
    STATUS_FAILED,
    STATUS_NEW,
    claim_new_transactions,
    count_new_transactions,
    finalize_run,
    mark_transaction_analyzing,
    process_run_item,
    run_batch_analysis,
)
from app.services.financial_investigation import build_investigation
from app.workflows.financial_workflow import WORKFLOW_VERSION, run_financial_workflow


router = APIRouter(
    prefix="/api/workflows",
    tags=["Workflows"],
)


def _to_response(db: Session, transaction_id: int, result: dict) -> WorkflowRunResponse:
    workflow_status = result.get("workflow_status", "UNKNOWN")
    steps = [
        WorkflowStepResult(
            name=step["name"],
            label=step["label"],
            status=step["status"],
            detail=step.get("detail"),
        )
        for step in result.get("steps", [])
    ]

    investigation = None
    if workflow_status in {"COMPLETED", "NORMAL"}:
        transaction = db.get(Transaction, transaction_id)
        if transaction:
            investigation = build_investigation(db, transaction)

    return WorkflowRunResponse(
        transaction_id=transaction_id,
        workflow_status=workflow_status,
        workflow_version=WORKFLOW_VERSION,
        steps=steps,
        error=result.get("error"),
        investigation=investigation,
    )


def _run_to_response(run: AnalysisRun, *, include_items: bool = True) -> AnalysisRunResponse:
    items = []
    if include_items:
        items = [
            AnalysisRunItemResponse.model_validate(item)
            for item in (run.items or [])
        ]
    return AnalysisRunResponse(
        id=run.id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        mode=run.mode,
        status=run.status,
        batch_size=run.batch_size,
        total_transactions=run.total_transactions,
        successful=run.successful,
        failed=run.failed,
        high_risk=run.high_risk,
        medium_risk=run.medium_risk,
        low_risk=run.low_risk,
        remaining_new_after=run.remaining_new_after,
        items=items,
    )


@router.post(
    "/transactions/{transaction_id}/analyze",
    response_model=WorkflowRunResponse,
)
def analyze_transaction_workflow(
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """
    Run the LangGraph financial workflow for a transaction.

    Marks ANALYZING first to prevent duplicate concurrent analysis.
    """
    transaction = db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=404,
            detail=f"Transaction {transaction_id} not found",
        )

    if transaction.analysis_status == STATUS_ANALYZING:
        # Allow if already analyzing by this request path; block only if stuck?
        # Re-entry from batch process_run_item already set ANALYZING — continue.
        pass
    else:
        mark_transaction_analyzing(db, transaction_id)

    try:
        result = run_financial_workflow(db, transaction_id)
    except RuntimeError as exc:
        txn = db.get(Transaction, transaction_id)
        if txn:
            txn.analysis_status = STATUS_FAILED
            db.commit()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _to_response(db, transaction_id, result)


@router.post(
    "/claim-new",
    response_model=ClaimBatchResponse,
)
def claim_new_batch(
    limit: int = Query(10, ge=1, le=50),
    mode: str = Query("NEW"),
    db: Session = Depends(get_db),
):
    """
    Claim newest NEW transactions (mark ANALYZING) without running the workflow yet.

    Used by the frontend for live progress: claim → analyze each → finalize.
    """
    run = claim_new_transactions(db, limit=limit, mode=mode.upper())
    items = (
        db.query(AnalysisRunItem)
        .filter(AnalysisRunItem.run_id == run.id)
        .order_by(AnalysisRunItem.id.asc())
        .all()
    )
    return ClaimBatchResponse(
        run_id=run.id,
        mode=run.mode,
        status=run.status,
        claimed=len(items),
        remaining_new=count_new_transactions(db),
        transaction_ids=[item.transaction_id for item in items],
    )


@router.post(
    "/runs/{run_id}/items/{transaction_id}/process",
    response_model=ProcessItemResponse,
)
def process_claimed_item(
    run_id: int,
    transaction_id: int,
    db: Session = Depends(get_db),
):
    """Process one claimed transaction inside an analysis run."""
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")

    try:
        item = process_run_item(db, run_id=run_id, transaction_id=transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ProcessItemResponse(
        run_id=run_id,
        transaction_id=transaction_id,
        status=item.status,
        workflow_status=item.workflow_status,
        risk_level=item.risk_level,
        error=item.error,
        remaining_new=count_new_transactions(db),
    )


@router.post(
    "/runs/{run_id}/finalize",
    response_model=AnalysisRunResponse,
)
def finalize_analysis_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = db.get(AnalysisRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    finalized = finalize_run(db, run_id)
    finalized = (
        db.query(AnalysisRun)
        .options(joinedload(AnalysisRun.items))
        .filter(AnalysisRun.id == finalized.id)
        .one()
    )
    return _run_to_response(finalized)


@router.post(
    "/analyze-new",
    response_model=BatchWorkflowResponse,
)
def analyze_new_transactions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Analyze up to `limit` NEW transactions in one server-side batch.

    Claims rows as ANALYZING first so concurrent clicks cannot double-process.
    """
    run = run_batch_analysis(db, limit=limit, mode="NEW")
    run = (
        db.query(AnalysisRun)
        .options(joinedload(AnalysisRun.items))
        .filter(AnalysisRun.id == run.id)
        .one()
    )

    completed = sum(1 for i in run.items if i.workflow_status == "COMPLETED")
    normal = sum(1 for i in run.items if i.workflow_status == "NORMAL")

    return BatchWorkflowResponse(
        status="completed" if run.failed == 0 else "completed_with_errors",
        run_id=run.id,
        requested=limit,
        processed=run.total_transactions,
        successful=run.successful,
        completed=completed,
        normal=normal,
        failed=run.failed,
        remaining_new=run.remaining_new_after or 0,
        high_risk=run.high_risk,
        medium_risk=run.medium_risk,
        low_risk=run.low_risk,
        results=[
            BatchWorkflowItem(
                transaction_id=item.transaction_id,
                workflow_status=item.workflow_status or item.status,
                status=item.status,
                risk_level=item.risk_level,
                error=item.error,
            )
            for item in run.items
        ],
    )


@router.get("/runs", response_model=PaginatedAnalysisRunsResponse)
def list_analysis_runs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(AnalysisRun).order_by(AnalysisRun.started_at.desc())
    total = query.count()
    pages = ceil(total / limit) if total else 0
    rows = (
        query.options(joinedload(AnalysisRun.items))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return PaginatedAnalysisRunsResponse(
        items=[_run_to_response(row) for row in rows],
        page=page,
        limit=limit,
        total=total,
        pages=pages,
    )


@router.get("/runs/{run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(
    run_id: int,
    db: Session = Depends(get_db),
):
    run = (
        db.query(AnalysisRun)
        .options(joinedload(AnalysisRun.items))
        .filter(AnalysisRun.id == run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    return _run_to_response(run)


@router.get("/new-count")
def get_new_transaction_count(db: Session = Depends(get_db)):
    return {
        "new": count_new_transactions(db),
        "analyzing": db.query(Transaction)
        .filter(Transaction.analysis_status == STATUS_ANALYZING)
        .count(),
        "failed": db.query(Transaction)
        .filter(Transaction.analysis_status == STATUS_FAILED)
        .count(),
    }


@router.post("/reset-stuck")
def reset_stuck_analyzing(
    db: Session = Depends(get_db),
):
    """
    Recover transactions left in ANALYZING if a client disconnected mid-batch.
    Moves them back to NEW so they can be claimed again.
    """
    stuck = (
        db.query(Transaction)
        .filter(Transaction.analysis_status == STATUS_ANALYZING)
        .all()
    )
    for txn in stuck:
        txn.analysis_status = STATUS_NEW

    abandoned = (
        db.query(AnalysisRun)
        .filter(AnalysisRun.status == "RUNNING")
        .all()
    )
    abandoned_ids = [run.id for run in abandoned]
    db.commit()

    for run_id in abandoned_ids:
        items = (
            db.query(AnalysisRunItem)
            .filter(
                AnalysisRunItem.run_id == run_id,
                AnalysisRunItem.status.in_(["PENDING", "RUNNING"]),
            )
            .all()
        )
        for item in items:
            item.status = "SKIPPED"
            item.workflow_status = "SKIPPED"
        db.commit()
        finalize_run(db, run_id)

    return {"reset": len(stuck), "new": count_new_transactions(db)}

