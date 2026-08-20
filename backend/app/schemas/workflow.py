from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.financial_review import FinancialInvestigationResponse


class WorkflowStepResult(BaseModel):
    name: str
    label: str
    status: str
    detail: str | None = None


class WorkflowRunResponse(BaseModel):
    transaction_id: int
    workflow_status: str
    workflow_version: str
    steps: list[WorkflowStepResult] = Field(default_factory=list)
    error: str | None = None
    investigation: FinancialInvestigationResponse | None = None


class BatchWorkflowItem(BaseModel):
    transaction_id: int
    workflow_status: str
    status: str | None = None
    risk_level: str | None = None
    error: str | None = None


class BatchWorkflowResponse(BaseModel):
    status: str = "completed"
    run_id: int | None = None
    requested: int
    processed: int
    successful: int = 0
    completed: int = 0
    normal: int = 0
    failed: int
    remaining_new: int = 0
    high_risk: int = 0
    medium_risk: int = 0
    low_risk: int = 0
    results: list[BatchWorkflowItem] = Field(default_factory=list)


class ClaimBatchResponse(BaseModel):
    run_id: int
    mode: str
    status: str
    claimed: int
    remaining_new: int
    transaction_ids: list[int] = Field(default_factory=list)


class ProcessItemResponse(BaseModel):
    run_id: int
    transaction_id: int
    status: str
    workflow_status: str | None = None
    risk_level: str | None = None
    error: str | None = None
    remaining_new: int = 0


class AnalysisRunItemResponse(BaseModel):
    id: int
    transaction_id: int
    status: str
    workflow_status: str | None = None
    risk_level: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AnalysisRunResponse(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None = None
    mode: str
    status: str
    batch_size: int
    total_transactions: int
    successful: int
    failed: int
    high_risk: int
    medium_risk: int
    low_risk: int
    remaining_new_after: int | None = None
    items: list[AnalysisRunItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaginatedAnalysisRunsResponse(BaseModel):
    items: list[AnalysisRunResponse]
    page: int
    limit: int
    total: int
    pages: int
