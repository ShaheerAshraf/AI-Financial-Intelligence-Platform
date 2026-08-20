"""
LangGraph orchestration for the financial intelligence pipeline.

Agents perform reasoning; this module routes between existing agent functions.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import RunnableConfig
from sqlalchemy.orm import Session

from app.agents.financial_review_runner import (
    build_review_evidence,
    save_financial_review,
)
from app.agents.invoice_verification_runner import run_verification_for_transaction
from app.agents.persist import build_anomaly_evidence, save_transaction_analysis
from app.agents.review_agent import review_transaction
from app.agents.transaction_agent import analyze_transaction
from app.models.anomaly_result import AnomalyResult
from app.models.invoice import Invoice
from app.models.invoice_verification import InvoiceVerification
from app.models.transaction import Transaction
from app.models.transaction_analysis import TransactionAnalysis
from app.services.invoice_extractor import EXTRACTION_STATUS_EXTRACTED
from app.services.anomaly_scoring import score_transaction_anomaly

SUSPICIOUS_STATUSES = {"HIGH", "MEDIUM", "LOW"}
WORKFLOW_VERSION = "financial_workflow_v1"


class FinancialState(TypedDict, total=False):
    transaction_id: int
    transaction: dict[str, Any] | None
    anomaly_result: dict[str, Any] | None
    is_suspicious: bool
    workflow_status: str
    steps: Annotated[list[dict[str, Any]], operator.add]
    error: str | None
    transaction_analysis: dict[str, Any] | None
    invoice: dict[str, Any] | None
    invoice_available: bool
    invoice_verification: dict[str, Any] | None
    financial_review: dict[str, Any] | None


def _get_db(config: RunnableConfig) -> Session:
    db = config.get("configurable", {}).get("db")
    if db is None:
        raise RuntimeError("Database session missing from workflow config")
    return db


def _step(name: str, label: str, status: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "steps": [
            {
                "name": name,
                "label": label,
                "status": status,
                "detail": detail,
            }
        ]
    }


def _transaction_dict(transaction: Transaction) -> dict[str, Any]:
    return {
        "id": transaction.id,
        "amount": float(transaction.amount),
        "vendor_id": transaction.vendor_id,
        "category_id": transaction.category_id,
        "date": transaction.transaction_date.isoformat(),
        "currency": transaction.currency,
        "description": transaction.description,
    }


def _anomaly_dict(anomaly: AnomalyResult) -> dict[str, Any]:
    return {
        "score": anomaly.anomaly_score,
        "status": anomaly.status,
        "reason": anomaly.reason,
        "model_version": anomaly.model_version,
        "detected_at": anomaly.detected_at.isoformat(),
    }


def _invoice_dict(invoice: Invoice) -> dict[str, Any]:
    return {
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "vendor_name": invoice.vendor_name,
        "amount": float(invoice.amount) if invoice.amount is not None else None,
        "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        "currency": invoice.currency,
        "extraction_status": invoice.extraction_status,
    }


def _analysis_dict(analysis: TransactionAnalysis) -> dict[str, Any]:
    return {
        "risk_level": analysis.risk_level,
        "summary": analysis.summary,
        "recommendation": analysis.recommendation,
        "findings": analysis.findings,
    }


def _verification_dict(result) -> dict[str, Any]:
    return {
        "status": result.match_status,
        "summary": result.summary,
        "recommendation": result.recommendation,
        "mismatches": result.mismatches,
    }


def _review_dict(result) -> dict[str, Any]:
    return {
        "risk_level": result.final_risk_level,
        "decision": result.decision,
        "summary": result.summary,
        "recommendation": result.recommendation,
        "findings": result.findings,
    }


def load_transaction(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    db = _get_db(config)
    transaction_id = state["transaction_id"]
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        return {
            "error": f"Transaction {transaction_id} not found",
            "workflow_status": "FAILED",
            **_step("load_transaction", "Transaction loaded", "FAILED", "Not found"),
        }
    return {
        "transaction": _transaction_dict(transaction),
        "workflow_status": "RUNNING",
        **_step("load_transaction", "Transaction loaded", "OK"),
    }


def run_anomaly_check(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        return {}

    db = _get_db(config)
    transaction_id = state["transaction_id"]
    anomaly = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )

    # New transactions are not in the batch ML table — score them online.
    if anomaly is None:
        try:
            anomaly = score_transaction_anomaly(db, transaction_id)
        except Exception as exc:
            return {
                "error": f"Anomaly scoring failed: {exc}",
                "workflow_status": "FAILED",
                **_step("run_anomaly_check", "Anomaly detection", "FAILED", str(exc)),
            }

    is_suspicious = anomaly.status in SUSPICIOUS_STATUSES
    # NORMAL status from online/batch scoring → finish without agents
    if anomaly.status == "NORMAL":
        return {
            "anomaly_result": _anomaly_dict(anomaly),
            "is_suspicious": False,
            "workflow_status": "NORMAL",
            **_step(
                "run_anomaly_check",
                "Anomaly detection",
                "NORMAL",
                anomaly.reason,
            ),
        }

    status_label = anomaly.status if is_suspicious else "NORMAL"
    return {
        "anomaly_result": _anomaly_dict(anomaly),
        "is_suspicious": is_suspicious,
        "workflow_status": "ANOMALY" if is_suspicious else "NORMAL",
        **_step("run_anomaly_check", "Anomaly detection", status_label, anomaly.reason),
    }


def analyze_transaction_node(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        return {}

    db = _get_db(config)
    transaction_id = state["transaction_id"]
    transaction = db.get(Transaction, transaction_id)
    anomaly = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )
    if not transaction or not anomaly:
        return {
            "error": "Missing transaction or anomaly for Agent 1",
            "workflow_status": "FAILED",
            **_step("analyze_transaction", "Transaction analysis", "FAILED"),
        }

    try:
        evidence = build_anomaly_evidence(transaction, anomaly)
        result = analyze_transaction(evidence)
        row = save_transaction_analysis(
            db,
            transaction_id=transaction_id,
            analysis=result,
        )
        return {
            "transaction_analysis": _analysis_dict(row),
            **_step(
                "analyze_transaction",
                "Transaction analysis",
                "OK",
                result.risk_level,
            ),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "workflow_status": "FAILED",
            **_step("analyze_transaction", "Transaction analysis", "FAILED", str(exc)),
        }


def load_invoice(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        return {}

    db = _get_db(config)
    invoice = (
        db.query(Invoice)
        .filter(
            Invoice.transaction_id == state["transaction_id"],
            Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED,
        )
        .order_by(Invoice.id.asc())
        .first()
    )

    if invoice is None:
        return {
            "invoice": None,
            "invoice_available": False,
            **_step("load_invoice", "Invoice check", "SKIPPED", "No invoice attached"),
        }

    return {
        "invoice": _invoice_dict(invoice),
        "invoice_available": True,
        **_step(
            "load_invoice",
            "Invoice check",
            "OK",
            invoice.invoice_number or f"invoice #{invoice.id}",
        ),
    }


def verify_invoice_node(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        return {}

    db = _get_db(config)
    transaction_id = state["transaction_id"]

    try:
        row = run_verification_for_transaction(db, transaction_id)
        return {
            "invoice_verification": {
                "status": row.match_status,
                "summary": row.summary,
                "recommendation": row.recommendation,
                "mismatches": row.mismatches or [],
                "field_comparisons": row.field_comparisons or [],
            },
            **_step(
                "verify_invoice",
                "Invoice verification",
                row.match_status,
                row.summary,
            ),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "workflow_status": "FAILED",
            **_step("verify_invoice", "Invoice verification", "FAILED", str(exc)),
        }


def financial_review_node(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        return {}

    db = _get_db(config)
    transaction_id = state["transaction_id"]
    transaction = db.get(Transaction, transaction_id)
    anomaly = (
        db.query(AnomalyResult)
        .filter(AnomalyResult.transaction_id == transaction_id)
        .order_by(AnomalyResult.detected_at.desc())
        .first()
    )
    analysis = (
        db.query(TransactionAnalysis)
        .filter(TransactionAnalysis.transaction_id == transaction_id)
        .order_by(TransactionAnalysis.created_at.desc())
        .first()
    )
    if not transaction or not anomaly or not analysis:
        return {
            "error": "Missing data for Agent 3",
            "workflow_status": "FAILED",
            **_step("financial_review", "Financial review", "FAILED"),
        }

    invoices = (
        db.query(Invoice)
        .filter(
            Invoice.transaction_id == transaction_id,
            Invoice.extraction_status == EXTRACTION_STATUS_EXTRACTED,
        )
        .order_by(Invoice.id.asc())
        .all()
    )
    verifications = (
        db.query(InvoiceVerification)
        .filter(InvoiceVerification.transaction_id == transaction_id)
        .order_by(InvoiceVerification.id.asc())
        .all()
    )

    try:
        evidence = build_review_evidence(
            transaction,
            anomaly,
            analysis,
            verifications,
            invoices,
        )
        result = review_transaction(evidence)
        save_financial_review(
            db,
            transaction_id=transaction_id,
            result=result,
        )
        return {
            "financial_review": _review_dict(result),
            **_step(
                "financial_review",
                "Financial review",
                result.final_risk_level,
                result.decision,
            ),
        }
    except Exception as exc:
        return {
            "error": str(exc),
            "workflow_status": "FAILED",
            **_step("financial_review", "Financial review", "FAILED", str(exc)),
        }


def persist_results(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    if state.get("error"):
        db = _get_db(config)
        db.rollback()
        transaction = db.get(Transaction, state["transaction_id"])
        if transaction is not None:
            transaction.analysis_status = "ANALYSIS_FAILED"
            db.commit()
        return {
            "workflow_status": "FAILED",
            **_step("persist_results", "Analysis complete", "FAILED", state["error"]),
        }

    db = _get_db(config)
    transaction = db.get(Transaction, state["transaction_id"])
    if transaction is not None:
        transaction.analysis_status = "ANALYZED"
    db.commit()
    return {
        "workflow_status": "COMPLETED",
        **_step("persist_results", "Analysis complete", "OK"),
    }


def route_after_anomaly(state: FinancialState) -> Literal["analyze", "mark_normal"]:
    if state.get("error"):
        return "mark_normal"
    if state.get("is_suspicious"):
        return "analyze"
    return "mark_normal"


def mark_normal_complete(state: FinancialState, config: RunnableConfig) -> dict[str, Any]:
    """Non-suspicious transactions: mark ANALYZED and end without agents."""
    db = _get_db(config)
    transaction = db.get(Transaction, state["transaction_id"])
    if transaction is not None:
        transaction.analysis_status = "ANALYZED"
    db.commit()
    return {
        "workflow_status": "NORMAL",
        **_step("mark_normal", "Analysis complete", "OK", "No unusual activity detected"),
    }


def route_after_invoice(state: FinancialState) -> Literal["verify", "review"]:
    # Always run Agent 2 (verifies invoice or persists NOT_PROVIDED).
    if state.get("error"):
        return "review"
    return "verify"


def route_after_analysis(state: FinancialState) -> Literal["continue", "fail"]:
    if state.get("error"):
        return "fail"
    return "continue"


def route_after_verify(state: FinancialState) -> Literal["continue", "fail"]:
    if state.get("error"):
        return "fail"
    return "continue"


def build_financial_workflow():
    graph = StateGraph(FinancialState)

    graph.add_node("load_transaction", load_transaction)
    graph.add_node("run_anomaly_check", run_anomaly_check)
    graph.add_node("mark_normal_complete", mark_normal_complete)
    graph.add_node("analyze_transaction", analyze_transaction_node)
    graph.add_node("load_invoice", load_invoice)
    graph.add_node("verify_invoice", verify_invoice_node)
    graph.add_node("financial_review", financial_review_node)
    graph.add_node("persist_results", persist_results)

    graph.add_edge(START, "load_transaction")
    graph.add_edge("load_transaction", "run_anomaly_check")
    graph.add_conditional_edges(
        "run_anomaly_check",
        route_after_anomaly,
        {"analyze": "analyze_transaction", "mark_normal": "mark_normal_complete"},
    )
    graph.add_edge("mark_normal_complete", END)
    graph.add_conditional_edges(
        "analyze_transaction",
        route_after_analysis,
        {"continue": "load_invoice", "fail": "persist_results"},
    )
    graph.add_conditional_edges(
        "load_invoice",
        route_after_invoice,
        {"verify": "verify_invoice", "review": "financial_review"},
    )
    graph.add_conditional_edges(
        "verify_invoice",
        route_after_verify,
        {"continue": "financial_review", "fail": "persist_results"},
    )
    graph.add_edge("financial_review", "persist_results")
    graph.add_edge("persist_results", END)

    return graph.compile()


def run_financial_workflow(db: Session, transaction_id: int) -> dict[str, Any]:
    """
    Execute the LangGraph pipeline for a single transaction.

    Returns the final workflow state including step log and agent outputs.
    """
    workflow = build_financial_workflow()
    initial_state: FinancialState = {
        "transaction_id": transaction_id,
        "steps": [],
    }
    try:
        final_state = workflow.invoke(
            initial_state,
            config={"configurable": {"db": db}},
        )
    except Exception as exc:
        db.rollback()
        raise RuntimeError(f"Workflow failed: {exc}") from exc

    if final_state.get("error") and final_state.get("workflow_status") not in {
        "NORMAL",
        "COMPLETED",
    }:
        db.rollback()

    return dict(final_state)
