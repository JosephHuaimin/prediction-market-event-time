from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

INPUT_PATH = Path("data/processed/event_time_metrics_by_timepoint.csv")
OUTPUT_PATH = Path("results/event_time_brier_vs_time.png")

TIMEPOINT_LABELS = {
    "1d_before_close": "1d",
    "6h_before_close": "6h",
    "1h_before_close": "1h",
    "last_preclose": "last",
}


def main():
    df = pd.read_csv(INPUT_PATH, low_memory=False)

    plt.figure(figsize=(8, 6))
    plt.plot(
        df["timepoint"].map(TIMEPOINT_LABELS),
        df["brier_score"],
        marker="o",
    )

    for _, row in df.iterrows():
        plt.annotate(
            int(row["market_count"]),
            (TIMEPOINT_LABELS[row["timepoint"]], row["brier_score"]),
            textcoords="offset points",
            xytext=(5, 5),
        )

    plt.xlabel("Time To Close")
    plt.ylabel("Brier Score")
    plt.title("Brier Score vs Time To Close")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300)
    plt.close()

    print("Done plotting Brier vs time-to-close.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
