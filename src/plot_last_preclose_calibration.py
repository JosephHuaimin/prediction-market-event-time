from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

CALIBRATION_PATH = Path("data/processed/event_time_last_preclose_calibration.csv")
LAST_DATASET_PATH = Path("data/processed/event_time_last_preclose_dataset.csv")
OUTPUT_PATH = Path("results/event_time_last_preclose_calibration.png")


def main():
    calibration_df = pd.read_csv(CALIBRATION_PATH, low_memory=False)
    last_df = pd.read_csv(LAST_DATASET_PATH, low_memory=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].scatter(
        calibration_df["avg_predicted_prob"],
        calibration_df["actual_yes_rate"],
        s=60,
    )
    axes[0].plot([0, 1], [0, 1], linestyle="--")

    for _, row in calibration_df.iterrows():
        axes[0].annotate(
            int(row["market_count"]),
            (row["avg_predicted_prob"], row["actual_yes_rate"]),
            textcoords="offset points",
            xytext=(5, 5),
        )

    axes[0].set_xlabel("Average Predicted Probability")
    axes[0].set_ylabel("Actual Yes Rate")
    axes[0].set_title("Last Pre-close Calibration")
    axes[0].set_xlim(0, 1)
    axes[0].set_ylim(0, 1)

    axes[1].hist(last_df["implied_prob"], bins=10, range=(0, 1), edgecolor="black")
    axes[1].set_xlabel("Last Pre-close Probability")
    axes[1].set_ylabel("Market Count")
    axes[1].set_title("Last Pre-close Probability Distribution")
    axes[1].set_xlim(0, 1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=300)
    plt.close()

    print("Done plotting last pre-close calibration figure.")
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
