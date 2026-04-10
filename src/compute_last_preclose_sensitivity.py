from pathlib import Path

import pandas as pd

INPUT_PATH = Path("data/processed/event_time_timepoint_probabilities.csv")
OUTPUT_PATH = Path("data/processed/event_time_last_preclose_gap_sensitivity.csv")

GAP_CAPS = [
    ("no_cap", None),
    ("within_168h", 168),
    ("within_72h", 72),
    ("within_24h", 24),
    ("within_6h", 6),
    ("within_1h", 1),
]


def main():
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df["outcome"] = pd.to_numeric(df["outcome"], errors="coerce")
    df["implied_prob"] = pd.to_numeric(df["implied_prob"], errors="coerce")
    df["time_diff_seconds"] = pd.to_numeric(df["time_diff_seconds"], errors="coerce")
    df["matched"] = df["matched"].fillna(False).astype(bool)

    last_df = df[
        (df["timepoint"] == "last_preclose") &
        df["matched"] &
        df["outcome"].notna() &
        df["implied_prob"].notna()
    ].copy()

    rows = []

    for label, max_gap_hours in GAP_CAPS:
        subset = last_df.copy()
        if max_gap_hours is not None:
            subset = subset[subset["time_diff_seconds"] <= max_gap_hours * 3600].copy()

        if len(subset) == 0:
            continue

        yes_df = subset[subset["outcome"] == 1].copy()
        no_df = subset[subset["outcome"] == 0].copy()

        rows.append(
            {
                "gap_rule": label,
                "market_count": subset["ticker"].nunique(),
                "brier_score": ((subset["implied_prob"] - subset["outcome"]) ** 2).mean(),
                "mae": (subset["implied_prob"] - subset["outcome"]).abs().mean(),
                "eventual_yes_avg_prob": yes_df["implied_prob"].mean(),
                "eventual_no_avg_prob": no_df["implied_prob"].mean(),
            }
        )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUTPUT_PATH, index=False)

    print("Done computing last pre-close gap sensitivity.")
    print(out_df.to_string(index=False))
    print()
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
