from anomaly_detector import build_anomaly_report, detect_anomalies
from data_loader import load_transactions
from features import create_features
from save_results import MODEL_VERSION, save_anomaly_results

transactions = load_transactions()
features = create_features(transactions)

print("\nFeatures:")
print(features.head())

print("\nFeature shape:")
print(features.shape)

print("\nHistorical feature validation:")
print(
    features[
        [
            "amount",
            "vendor_previous_avg",
            "vendor_previous_std",
            "category_previous_avg",
            "amount_vs_vendor_previous_avg",
            "amount_vs_category_previous_avg",
        ]
    ].head(10)
)

anomaly_results = detect_anomalies(features)
report = build_anomaly_report(transactions, anomaly_results)

print("\nAnomaly report (top suspicious):")
print(
    report[report["status"] != "NORMAL"]
    .head(20)
    .to_string(index=False)
)

print("\nNumber of anomalies:")
print((anomaly_results["anomaly_prediction"] == -1).sum())

print("\nHIGH severity count:")
print((report["status"] == "HIGH").sum())

saved_count = save_anomaly_results(report)
print(f"\nSaved {saved_count} anomaly results to PostgreSQL ({MODEL_VERSION}).")
