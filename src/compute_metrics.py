import json
from pathlib import Path

import pandas as pd

UNIVERSE_PATH = Path("data/processed/event_time_universe.csv")
UNIVERSE_STATS_PATH = Path("data/processed/event_time_universe_build_stats.json")
SAMPLE_PATH = Path("data/processed/event_time_stratified_sample.csv")
DOWNLOAD_SUMMARY_PATH = Path("data/processed/event_time_sample_candle_download_summary.csv")
TIMEPOINT_PATH = Path("data/processed/event_time_timepoint_probabilities.csv")

METRICS_PATH = Path("data/processed/event_time_metrics_by_timepoint.csv")
AVERAGE_PATHS_PATH = Path("data/processed/event_time_average_path_by_outcome.csv")
LAST_PRECLOSE_DATASET_PATH = Path("data/processed/event_time_last_preclose_dataset.csv")
LAST_PRECLOSE_CALIBRATION_PATH = Path("data/processed/event_time_last_preclose_calibration.csv")
SAMPLE_CONSTRUCTION_PATH = Path("data/processed/event_time_sample_construction_table.csv")

TIMEPOINT_ORDER = [
    "1d_before_close",
    "6h_before_close",
    "1h_before_close",
    "last_preclose",
]


def add_filter_counts(universe_df):
    universe_df = universe_df.copy()
    universe_df["open_time"] = pd.to_datetime(universe_df["open_time"], errors="coerce", utc=True)
    universe_df["close_time"] = pd.to_datetime(universe_df["close_time"], errors="coerce", utc=True)
    universe_df["outcome"] = pd.to_numeric(universe_df["outcome"], errors="coerce")

    resolved_binary_df = universe_df[
        (universe_df["market_type"] == "binary") &
        (universe_df["result"].isin(["yes", "no"])) &
        (universe_df["outcome"].notna())
    ].copy()

    valid_time_df = resolved_binary_df[
        resolved_binary_df["open_time"].notna() &
        resolved_binary_df["close_time"].notna() &
        (resolved_binary_df["close_time"] >= resolved_binary_df["open_time"])
    ].copy()

    return {
        "after_resolved_binary_filter": len(resolved_binary_df),
        "after_valid_time_filter": len(valid_time_df),
        "after_date_window_filter": len(universe_df),
    }


def main():
    universe_df = pd.read_csv(UNIVERSE_PATH, low_memory=False)
    sample_df = pd.read_csv(SAMPLE_PATH, low_memory=False)
    download_summary_df = pd.read_csv(DOWNLOAD_SUMMARY_PATH, low_memory=False)
    timepoint_df = pd.read_csv(TIMEPOINT_PATH, low_memory=False)

    timepoint_df["outcome"] = pd.to_numeric(timepoint_df["outcome"], errors="coerce")
    timepoint_df["implied_prob"] = pd.to_numeric(timepoint_df["implied_prob"], errors="coerce")
    timepoint_df["matched"] = timepoint_df["matched"].fillna(False).astype(bool)

    valid_df = timepoint_df[
        timepoint_df["matched"] &
        timepoint_df["outcome"].notna() &
        timepoint_df["implied_prob"].notna()
    ].copy()

    valid_df["squared_error"] = (valid_df["implied_prob"] - valid_df["outcome"]) ** 2
    valid_df["absolute_error"] = (valid_df["implied_prob"] - valid_df["outcome"]).abs()

    metrics_df = (
        valid_df.groupby("timepoint", as_index=False)
        .agg(
            market_count=("ticker", "count"),
            brier_score=("squared_error", "mean"),
            mae=("absolute_error", "mean"),
            avg_implied_prob=("implied_prob", "mean"),
            actual_yes_rate=("outcome", "mean"),
        )
    )
    metrics_df["timepoint"] = pd.Categorical(
        metrics_df["timepoint"],
        categories=TIMEPOINT_ORDER,
        ordered=True,
    )
    metrics_df = metrics_df.sort_values("timepoint")
    metrics_df.to_csv(METRICS_PATH, index=False)

    average_paths_df = (
        valid_df.groupby(["timepoint", "outcome"], as_index=False)
        .agg(
            market_count=("ticker", "count"),
            avg_implied_prob=("implied_prob", "mean"),
        )
    )
    average_paths_df["outcome_label"] = average_paths_df["outcome"].map(
        {1: "eventual_yes", 0: "eventual_no"}
    )
    average_paths_df["timepoint"] = pd.Categorical(
        average_paths_df["timepoint"],
        categories=TIMEPOINT_ORDER,
        ordered=True,
    )
    average_paths_df = average_paths_df.sort_values(["outcome_label", "timepoint"])
    average_paths_df.to_csv(AVERAGE_PATHS_PATH, index=False)

    last_preclose_df = valid_df[valid_df["timepoint"] == "last_preclose"].copy()
    last_preclose_df.to_csv(LAST_PRECLOSE_DATASET_PATH, index=False)

    calibration_df = pd.DataFrame(
        columns=[
            "prob_bin",
            "market_count",
            "avg_predicted_prob",
            "actual_yes_rate",
            "avg_squared_error",
        ]
    )

    if len(last_preclose_df) > 0:
        quantile_count = min(6, last_preclose_df["implied_prob"].nunique())
        if quantile_count >= 2:
            last_preclose_df["prob_bin"] = pd.qcut(
                last_preclose_df["implied_prob"],
                q=quantile_count,
                duplicates="drop",
            )
            calibration_df = (
                last_preclose_df.groupby("prob_bin", as_index=False)
                .agg(
                    market_count=("ticker", "count"),
                    avg_predicted_prob=("implied_prob", "mean"),
                    actual_yes_rate=("outcome", "mean"),
                    avg_squared_error=("squared_error", "mean"),
                )
            )
            calibration_df["prob_bin"] = calibration_df["prob_bin"].astype(str)

    calibration_df.to_csv(LAST_PRECLOSE_CALIBRATION_PATH, index=False)

    build_stats = {}
    if UNIVERSE_STATS_PATH.exists():
        with open(UNIVERSE_STATS_PATH, "r", encoding="utf-8") as file:
            build_stats = json.load(file)

    filter_counts = add_filter_counts(universe_df)

    sample_construction_df = pd.DataFrame(
        [
            {
                "step": "raw_markets_scanned_total",
                "count": build_stats.get("raw_markets_scanned_total"),
            },
            {
                "step": "after_date_window_filter",
                "count": filter_counts["after_date_window_filter"],
            },
            {
                "step": "after_resolved_binary_filter",
                "count": filter_counts["after_resolved_binary_filter"],
            },
            {
                "step": "after_valid_time_filter",
                "count": filter_counts["after_valid_time_filter"],
            },
            {
                "step": "sampled_markets",
                "count": len(sample_df),
            },
            {
                "step": "candles_successfully_retrieved",
                "count": int(download_summary_df["success"].sum()),
            },
            {
                "step": "final_analysis_sample_last_preclose",
                "count": last_preclose_df["ticker"].nunique(),
            },
        ]
    )
    sample_construction_df.to_csv(SAMPLE_CONSTRUCTION_PATH, index=False)

    print("Done computing event-time metrics.")
    print("Metrics by timepoint:")
    print(metrics_df)
    print()
    print("Average path preview:")
    print(average_paths_df.head(8))
    print()
    print("Last pre-close sample size:", last_preclose_df["ticker"].nunique())
    print(f"Saved metrics to: {METRICS_PATH}")
    print(f"Saved average paths to: {AVERAGE_PATHS_PATH}")
    print(f"Saved calibration table to: {LAST_PRECLOSE_CALIBRATION_PATH}")
    print(f"Saved sample construction table to: {SAMPLE_CONSTRUCTION_PATH}")


if __name__ == "__main__":
    main()
