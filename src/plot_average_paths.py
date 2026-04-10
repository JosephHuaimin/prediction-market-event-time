from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

INPUT_PATH = Path("data/processed/event_time_average_path_by_outcome.csv")
OUTPUT_PATH = Path("results/event_time_average_paths.png")

TIMEPOINT_ORDER = [
    "1d_before_close",
    "6h_before_close",
    "1h_before_close",
    "last_preclose",
]
TIMEPOINT_LABELS = {
    "1d_before_close": "1d",
    "6h_before_close": "6h",
    "1h_before_close": "1h",
    "last_preclose": "last",
}
COLOR_MAP = {
    "eventual_yes": "#1f77b4",
    "eventual_no": "#d62728",
}


def main():
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df["timepoint"] = pd.Categorical(df["timepoint"], categories=TIMEPOINT_ORDER, ordered=True)
    df = df.sort_values(["outcome_label", "timepoint"])

    plt.figure(figsize=(8, 6))

    for outcome_label, group_df in df.groupby("outcome_label"):
        plt.plot(
            group_df["timepoint"].map(TIMEPOINT_LABELS),
            group_df["avg_implied_prob"],
            marker="o",
            label=outcome_label,
            color=COLOR_MAP.get(outcome_label),
        )

    plt.xlabel("Time To Close")
    plt.ylabel("Average Implied Probability")
    plt.title("Average Implied Probability Path by Eventual Outcome")
    plt.ylim(0, 1)
    plt.legend()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300)
    plt.close()

    print("Done plotting average probability paths.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
