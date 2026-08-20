from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnomalyResultResponse(BaseModel):
    id: int
    transaction_id: int
    anomaly_score: float
    status: str
    reason: str | None
    model_version: str
    detected_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnomalySummaryResponse(BaseModel):
    total_transactions: int
    total_anomalies: int
    high_risk: int
    medium_risk: int
    anomaly_rate: float
