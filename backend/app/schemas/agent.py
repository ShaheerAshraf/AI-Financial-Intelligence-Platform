from typing import Literal

from pydantic import BaseModel, Field


class AgentAnalysis(BaseModel):
    """Agent 1 — Transaction Analysis Agent output."""

    risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str


class InvoiceVerificationResult(BaseModel):
    """Agent 2 — Invoice Verification Agent output."""

    match_status: Literal[
        "MATCH",
        "AMOUNT_MISMATCH",
        "VENDOR_MISMATCH",
        "DATE_MISMATCH",
        "MULTIPLE_MISMATCHES",
        "INSUFFICIENT_EVIDENCE",
        "NOT_PROVIDED",
    ]
    summary: str
    mismatches: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str


class FinancialReviewResult(BaseModel):
    """Agent 3 — Financial Review Agent output."""

    final_risk_level: Literal["HIGH", "MEDIUM", "LOW"]
    decision: Literal["APPROVED", "MANUAL_REVIEW", "HIGH_RISK", "ESCALATE"]
    summary: str
    findings: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    recommendation: str
