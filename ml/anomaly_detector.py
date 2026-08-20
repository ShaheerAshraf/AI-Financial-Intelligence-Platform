import math

import pandas as pd
from sklearn.ensemble import IsolationForest


MODEL_EXCLUDE_COLS = {"id", "anomaly_prediction", "anomaly_score"}


def detect_anomalies(
    features: pd.DataFrame,
    contamination: float = 0.05,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Train IsolationForest on transaction features and score each row.

    Returns a copy of `features` with:
    - anomaly_prediction: -1 = anomaly, 1 = normal
    - anomaly_score: lower = more anomalous (decision_function)
    """
    model_cols = [col for col in features.columns if col not in MODEL_EXCLUDE_COLS]
    model_input = features[model_cols].fillna(0)

    model = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(model_input)

    results = features.copy()
    results["anomaly_prediction"] = model.predict(model_input)
    results["anomaly_score"] = model.decision_function(model_input)

    return results


def _status_from_score(score: float, prediction: int, high_threshold: float) -> str:
    if prediction == 1:
        return "NORMAL"
    if score <= high_threshold:
        return "HIGH"
    return "MEDIUM"


def _is_missing(value: float) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _reason_from_features(row: pd.Series) -> str:
    """Explain the anomaly using historical vendor/category features."""
    if int(row["anomaly_prediction"]) == 1:
        return "Normal"

    reasons: list[str] = []

    amount = float(row["amount"])
    vendor_avg = row["vendor_previous_avg"]
    vendor_std = row["vendor_previous_std"]
    amount_vs_vendor = row["amount_vs_vendor_previous_avg"]
    amount_vs_category = row["amount_vs_category_previous_avg"]

    if _is_missing(vendor_avg) and _is_missing(row["category_previous_avg"]):
        return "No historical vendor/category data yet"

    if not _is_missing(amount_vs_vendor):
        amount_vs_vendor = float(amount_vs_vendor)
        if amount_vs_vendor >= 3:
            reasons.append("Amount much higher than vendor historical average")
        elif amount_vs_vendor >= 2:
            reasons.append("Amount higher than vendor historical average")
        elif amount_vs_vendor > 0 and amount_vs_vendor <= 0.4:
            reasons.append("Amount much lower than vendor historical average")

    if not _is_missing(amount_vs_category):
        amount_vs_category = float(amount_vs_category)
        if amount_vs_category >= 3:
            reasons.append("Amount much higher than category historical average")
        elif amount_vs_category >= 2:
            reasons.append("Amount higher than category historical average")

    if (
        not _is_missing(vendor_std)
        and not _is_missing(vendor_avg)
        and float(vendor_std) > 0
    ):
        z_score = abs(amount - float(vendor_avg)) / float(vendor_std)
        if z_score >= 3:
            reasons.append("Outside normal vendor historical spend variation")
    elif (
        not _is_missing(vendor_avg)
        and float(vendor_avg) > 0
        and abs(amount - float(vendor_avg)) / float(vendor_avg) >= 0.5
    ):
        reasons.append("Unusual amount vs vendor historical average")

    if not reasons:
        return "Unusual combination of historical spend patterns"

    return "; ".join(reasons)


def build_anomaly_report(
    transactions: pd.DataFrame,
    anomaly_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join anomaly scores back to the original transaction rows by id.

    Returns a readable report with Status and Reason from historical features.
    """
    scores = anomaly_results.reset_index(drop=True).copy()

    if "id" not in scores.columns:
        raise ValueError("anomaly_results must include transaction id for joining")

    report = transactions.reset_index(drop=True).copy()
    score_cols = [
        "id",
        "anomaly_prediction",
        "anomaly_score",
        "vendor_previous_avg",
        "vendor_previous_std",
        "category_previous_avg",
        "amount_vs_vendor_previous_avg",
        "amount_vs_category_previous_avg",
    ]
    report = report.merge(scores[score_cols], on="id", how="inner")

    anomaly_scores = report.loc[
        report["anomaly_prediction"] == -1, "anomaly_score"
    ]
    high_threshold = (
        float(anomaly_scores.quantile(0.25))
        if not anomaly_scores.empty
        else 0.0
    )

    report["status"] = [
        _status_from_score(score, prediction, high_threshold)
        for score, prediction in zip(
            report["anomaly_score"],
            report["anomaly_prediction"],
            strict=True,
        )
    ]
    report["reason"] = report.apply(_reason_from_features, axis=1)

    report = report.rename(
        columns={
            "id": "transaction_id",
            "vendor_id": "vendor",
            "category_id": "category",
            "transaction_date": "date",
        }
    )

    columns = [
        "transaction_id",
        "amount",
        "vendor",
        "category",
        "date",
        "description",
        "anomaly_score",
        "status",
        "reason",
    ]
    return report[columns].sort_values("anomaly_score", ascending=True)
