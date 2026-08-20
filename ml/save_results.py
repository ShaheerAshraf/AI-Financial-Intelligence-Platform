import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.models.anomaly_result import AnomalyResult

MODEL_VERSION = "isolation_forest_v1"


def save_anomaly_results(
    report: pd.DataFrame,
    model_version: str = MODEL_VERSION,
) -> int:
    """
    Replace previous results for `model_version`, then insert flagged anomalies.

    Only rows with status != NORMAL are saved (Isolation Forest anomalies).
    Returns the number of rows inserted.
    """
    anomalies = report[report["status"] != "NORMAL"].copy()

    db = SessionLocal()
    try:
        db.query(AnomalyResult).filter(
            AnomalyResult.model_version == model_version
        ).delete(synchronize_session=False)

        for row in anomalies.itertuples(index=False):
            db.add(
                AnomalyResult(
                    transaction_id=int(row.transaction_id),
                    anomaly_score=float(row.anomaly_score),
                    status=str(row.status),
                    reason=None if pd.isna(row.reason) else str(row.reason),
                    model_version=model_version,
                    detected_at=datetime.utcnow(),
                )
            )

        db.commit()
        return len(anomalies)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
