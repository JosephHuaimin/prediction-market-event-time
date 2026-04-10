import argparse
from pathlib import Path

import numpy as np
import pandas as pd

UNIVERSE_PATH = Path("data/processed/event_time_universe.csv")
SAMPLE_PATH = Path("data/processed/event_time_stratified_sample.csv")
ALLOCATION_PATH = Path("data/processed/event_time_stratum_allocation.csv")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=600)
    parser.add_argument("--seed", type=int, default=20260409)
    parser.add_argument("--start-date", default="2025-04-01")
    parser.add_argument("--end-date", default="2026-03-31")
    return parser.parse_args()


def choose_liquidity_proxy(df):
    candidates = [
        "liquidity_dollars",
        "volume_fp",
        "open_interest_fp",
    ]

    for column in candidates:
        values = pd.to_numeric(df[column], errors="coerce")
        positive_count = int((values > 0).sum())
        if positive_count >= max(100, int(0.25 * len(df))):
            return column

    return "volume_fp"


def allocate_proportionally(stratum_counts, target_n):
    target_n = min(target_n, int(stratum_counts.sum()))
    exact = (stratum_counts / stratum_counts.sum()) * target_n
    base = np.floor(exact).astype(int)
    base = np.minimum(base, stratum_counts.astype(int))

    allocation = base.copy()
    remainder = exact - base

    remaining = target_n - int(allocation.sum())
    while remaining > 0:
        capacity = stratum_counts - allocation
        eligible = capacity[capacity > 0]
        if eligible.empty:
            break

        next_stratum = remainder[eligible.index].sort_values(ascending=False).index[0]
        allocation.loc[next_stratum] += 1
        remainder.loc[next_stratum] = -1
        remaining -= 1

    return allocation.astype(int)


def main():
    args = parse_args()

    df = pd.read_csv(UNIVERSE_PATH, low_memory=False)
    raw_universe_count = len(df)

    df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], errors="coerce", utc=True)
    df["volume_fp"] = pd.to_numeric(df["volume_fp"], errors="coerce")
    df["liquidity_dollars"] = pd.to_numeric(df["liquidity_dollars"], errors="coerce")
    df["open_interest_fp"] = pd.to_numeric(df["open_interest_fp"], errors="coerce")
    df["outcome"] = pd.to_numeric(df["outcome"], errors="coerce")

    resolved_binary_df = df[
        (df["market_type"] == "binary") &
        (df["result"].isin(["yes", "no"])) &
        (df["outcome"].notna())
    ].copy()

    valid_time_df = resolved_binary_df[
        resolved_binary_df["open_time"].notna() &
        resolved_binary_df["close_time"].notna() &
        (resolved_binary_df["close_time"] >= resolved_binary_df["open_time"])
    ].copy()

    start_ts = pd.Timestamp(args.start_date, tz="UTC")
    end_ts_exclusive = pd.Timestamp(args.end_date, tz="UTC") + pd.Timedelta(days=1)

    date_window_df = valid_time_df[
        (valid_time_df["close_time"] >= start_ts) &
        (valid_time_df["close_time"] < end_ts_exclusive)
    ].copy()

    if len(date_window_df) == 0:
        empty_df = pd.DataFrame()
        SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        empty_df.to_csv(SAMPLE_PATH, index=False)
        empty_df.to_csv(ALLOCATION_PATH, index=False)
        print("No markets available after filtering the event-time universe.")
        print(f"Saved empty sample to: {SAMPLE_PATH}")
        print(f"Saved empty allocation table to: {ALLOCATION_PATH}")
        return

    liquidity_proxy_column = choose_liquidity_proxy(date_window_df)
    date_window_df["liquidity_proxy"] = pd.to_numeric(
        date_window_df[liquidity_proxy_column],
        errors="coerce",
    )

    positive_proxy_mask = date_window_df["liquidity_proxy"] > 0
    if positive_proxy_mask.sum() >= 3:
        ranked_proxy = date_window_df.loc[positive_proxy_mask, "liquidity_proxy"].rank(
            method="first"
        )
        date_window_df.loc[positive_proxy_mask, "liquidity_bucket"] = pd.qcut(
            ranked_proxy,
            q=3,
            labels=["low", "mid", "high"],
        ).astype(str)
    else:
        date_window_df["liquidity_bucket"] = "all"

    date_window_df["liquidity_bucket"] = date_window_df["liquidity_bucket"].fillna("all")
    date_window_df["resolution_month"] = (
        date_window_df["close_time"].dt.to_period("M").astype(str)
    )
    date_window_df["stratum"] = (
        date_window_df["resolution_month"] + "__" + date_window_df["liquidity_bucket"]
    )

    stratum_counts = date_window_df["stratum"].value_counts().sort_index()
    stratum_allocation = allocate_proportionally(stratum_counts, args.sample_size)

    sampled_parts = []
    allocation_rows = []

    for stratum, target_n in stratum_allocation.items():
        stratum_df = date_window_df[date_window_df["stratum"] == stratum].copy()
        sampled_df = stratum_df.sample(n=target_n, random_state=args.seed)
        sampled_parts.append(sampled_df)

        resolution_month, liquidity_bucket = stratum.split("__", 1)
        allocation_rows.append(
            {
                "resolution_month": resolution_month,
                "liquidity_bucket": liquidity_bucket,
                "available_count": len(stratum_df),
                "sampled_count": target_n,
            }
        )

    sample_df = pd.concat(sampled_parts, ignore_index=True)
    sample_df = sample_df.sort_values(
        ["resolution_month", "liquidity_bucket", "ticker"]
    ).copy()
    sample_df["sample_seed"] = args.seed
    sample_df["liquidity_proxy_column"] = liquidity_proxy_column

    allocation_df = pd.DataFrame(allocation_rows).sort_values(
        ["resolution_month", "liquidity_bucket"]
    )

    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    sample_df.to_csv(SAMPLE_PATH, index=False)
    allocation_df.to_csv(ALLOCATION_PATH, index=False)

    print("Done drawing stratified sample.")
    print("Raw universe rows:", raw_universe_count)
    print("After resolved/binary filter:", len(resolved_binary_df))
    print("After valid-time filter:", len(valid_time_df))
    print("After date-window filter:", len(date_window_df))
    print("Liquidity proxy column:", liquidity_proxy_column)
    print("Sample size drawn:", len(sample_df))
    print()
    print("Allocation preview:")
    print(allocation_df.head(12))
    print()
    print(f"Saved sample to: {SAMPLE_PATH}")
    print(f"Saved allocation table to: {ALLOCATION_PATH}")


if __name__ == "__main__":
    main()
