import pandas as pd


def _previous_expanding_mean(series: pd.Series) -> pd.Series:
    return series.shift(1).expanding(min_periods=1).mean()


def _previous_expanding_std(series: pd.Series) -> pd.Series:
    # Need at least 2 prior points for a real std; otherwise NaN
    return series.shift(1).expanding(min_periods=2).std()


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()

    # Convert transaction date
    data["transaction_date"] = pd.to_datetime(data["transaction_date"])

    # Chronological order so "previous" means earlier transactions only
    sort_cols = ["transaction_date"]
    if "id" in data.columns:
        sort_cols.append("id")
    data = data.sort_values(sort_cols).reset_index(drop=True)

    # Date-based features
    data["transaction_month"] = data["transaction_date"].dt.month
    data["transaction_day"] = data["transaction_date"].dt.day
    data["transaction_day_of_week"] = data["transaction_date"].dt.dayofweek

    # Historical vendor / category stats (exclude current transaction)
    data["vendor_previous_avg"] = data.groupby("vendor_id", sort=False)[
        "amount"
    ].transform(_previous_expanding_mean)
    data["vendor_previous_std"] = data.groupby("vendor_id", sort=False)[
        "amount"
    ].transform(_previous_expanding_std)
    data["category_previous_avg"] = data.groupby("category_id", sort=False)[
        "amount"
    ].transform(_previous_expanding_mean)

    # Ratios vs historical averages (NaN when no history — do not invent values)
    data["amount_vs_vendor_previous_avg"] = (
        data["amount"] / data["vendor_previous_avg"]
    )
    data["amount_vs_category_previous_avg"] = (
        data["amount"] / data["category_previous_avg"]
    )

    # Keep id for joining back to transactions; model excludes it later
    feature_cols = [
        "amount",
        "company_id",
        "vendor_id",
        "category_id",
        "transaction_month",
        "transaction_day",
        "transaction_day_of_week",
        "vendor_previous_avg",
        "vendor_previous_std",
        "category_previous_avg",
        "amount_vs_vendor_previous_avg",
        "amount_vs_category_previous_avg",
    ]
    if "id" in data.columns:
        feature_cols = ["id", *feature_cols]

    return data[feature_cols]
