import json
from pathlib import Path

import pandas as pd

BUILD_STATS_PATH = Path("data/processed/event_time_universe_build_stats.json")
UNIVERSE_PATH = Path("data/processed/event_time_universe.csv")
SAMPLE_PATH = Path("data/processed/event_time_stratified_sample.csv")
DOWNLOAD_SUMMARY_PATH = Path("data/processed/event_time_sample_candle_download_summary.csv")
TIMEPOINT_PATH = Path("data/processed/event_time_timepoint_probabilities.csv")
METRICS_PATH = Path("data/processed/event_time_metrics_by_timepoint.csv")
CALIBRATION_PATH = Path("data/processed/event_time_last_preclose_calibration.csv")

TIMEPOINT_TOLERANCES = {
    "1d_before_close": 6 * 3600,
    "6h_before_close": 2 * 3600,
    "1h_before_close": 30 * 60,
}


def print_header(title):
    print(title)
    print("-" * len(title))


def check_universe(build_stats, universe_df):
    print_header("Universe checks")
    print("Rows in universe CSV:", len(universe_df))
    print("Unique tickers in universe CSV:", universe_df["ticker"].nunique())
    print("Duplicate ticker rows:", int(universe_df.duplicated(subset=["ticker"]).sum()))

    close_time = pd.to_datetime(universe_df["close_time"], errors="coerce", utc=True)
    settlement_ts = pd.to_datetime(universe_df["settlement_ts"], errors="coerce", utc=True)
    anchor_time = close_time.fillna(settlement_ts)

    print("Min anchor timestamp:", anchor_time.min())
    print("Max anchor timestamp:", anchor_time.max())

    start_date = pd.Timestamp(build_stats["start_date"], tz="UTC")
    end_date = pd.Timestamp(build_stats["end_date"], tz="UTC") + pd.Timedelta(days=1)
    out_of_window = (~anchor_time.isna()) & ((anchor_time < start_date) | (anchor_time >= end_date))
    print("Rows outside configured window:", int(out_of_window.sum()))

    print("Unique markets pulled from metadata:", build_stats.get("unique_markets_pulled_from_metadata"))
    print("Unique markets in fixed date window:", build_stats.get("date_window_universe_count"))
    print()


def check_sample(universe_df, sample_df):
    print_header("Sample checks")
    print("Rows in sample CSV:", len(sample_df))
    print("Unique sampled tickers:", sample_df["ticker"].nunique())
    print("Duplicate sampled ticker rows:", int(sample_df.duplicated(subset=["ticker"]).sum()))
    sample_not_in_universe = ~sample_df["ticker"].isin(universe_df["ticker"])
    print("Sample tickers missing from universe:", int(sample_not_in_universe.sum()))
    print("Resolution months in sample:", sample_df["resolution_month"].nunique())
    print("Liquidity buckets in sample:", sorted(sample_df["liquidity_bucket"].dropna().unique().tolist()))
    print()


def check_downloads(sample_df, download_df):
    print_header("Download checks")
    success_df = download_df[download_df["success"]].copy()
    print("Rows in download summary:", len(download_df))
    print("Unique tickers in download summary:", download_df["ticker"].nunique())
    print("Successful downloads:", success_df["ticker"].nunique())
    missing_success = ~sample_df["ticker"].isin(success_df["ticker"])
    print("Sample tickers without successful candle download:", int(missing_success.sum()))
    print("Min candle count:", pd.to_numeric(success_df["candlestick_count"], errors="coerce").min())
    print("Median candle count:", pd.to_numeric(success_df["candlestick_count"], errors="coerce").median())
    print("Max candle count:", pd.to_numeric(success_df["candlestick_count"], errors="coerce").max())
    print()


def check_timepoints(sample_df, timepoint_df):
    print_header("Timepoint checks")
    timepoint_df["matched"] = timepoint_df["matched"].fillna(False).astype(bool)
    timepoint_df["time_diff_seconds"] = pd.to_numeric(
        timepoint_df["time_diff_seconds"], errors="coerce"
    )

    expected_rows = sample_df["ticker"].nunique() * 4
    print("Rows in timepoint file:", len(timepoint_df))
    print("Expected rows (sample x 4 timepoints):", expected_rows)
    print("Unique tickers in timepoint file:", timepoint_df["ticker"].nunique())
    print()

    for label in ["1d_before_close", "6h_before_close", "1h_before_close", "last_preclose"]:
        subset = timepoint_df[timepoint_df["timepoint"] == label].copy()
        matched = subset[subset["matched"]].copy()
        print(f"{label}:")
        print("  matched tickers:", matched["ticker"].nunique())

        if len(matched) > 0:
            print("  min time diff:", matched["time_diff_seconds"].min())
            print("  median time diff:", matched["time_diff_seconds"].median())
            print("  max time diff:", matched["time_diff_seconds"].max())

        if label in TIMEPOINT_TOLERANCES:
            over_tolerance = matched["time_diff_seconds"] > TIMEPOINT_TOLERANCES[label]
            print("  matched rows beyond tolerance:", int(over_tolerance.sum()))

    print()


def check_metrics(metrics_df, calibration_df):
    print_header("Metric checks")
    print(metrics_df.to_string(index=False))
    print()

    if len(metrics_df) > 1:
        print(
            "Brier change (1d -> last preclose):",
            round(
                float(metrics_df.iloc[0]["brier_score"]) - float(metrics_df.iloc[-1]["brier_score"]),
                6,
            ),
        )
    print("Calibration bin count:", len(calibration_df))
    print()


def main():
    with open(BUILD_STATS_PATH, "r", encoding="utf-8") as file:
        build_stats = json.load(file)

    universe_df = pd.read_csv(UNIVERSE_PATH, low_memory=False)
    sample_df = pd.read_csv(SAMPLE_PATH, low_memory=False)
    download_df = pd.read_csv(DOWNLOAD_SUMMARY_PATH, low_memory=False)
    timepoint_df = pd.read_csv(TIMEPOINT_PATH, low_memory=False)
    metrics_df = pd.read_csv(METRICS_PATH, low_memory=False)
    calibration_df = pd.read_csv(CALIBRATION_PATH, low_memory=False)

    check_universe(build_stats, universe_df)
    check_sample(universe_df, sample_df)
    check_downloads(sample_df, download_df)
    check_timepoints(sample_df, timepoint_df)
    check_metrics(metrics_df, calibration_df)

    print("Reasonableness check complete.")


if __name__ == "__main__":
    main()
