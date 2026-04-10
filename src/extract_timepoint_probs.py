import json
from pathlib import Path

import pandas as pd

SAMPLE_PATH = Path("data/processed/event_time_stratified_sample.csv")
CANDLE_DIR = Path("data/raw/event_time_sample_candles")
OUTPUT_PATH = Path("data/processed/event_time_timepoint_probabilities.csv")

TIMEPOINTS = [
    ("1d_before_close", pd.Timedelta(days=1), 6 * 3600),
    ("6h_before_close", pd.Timedelta(hours=6), 2 * 3600),
    ("1h_before_close", pd.Timedelta(hours=1), 30 * 60),
]


def extract_close_probability(candle):
    price_block = candle.get("price", {})

    for key in ["close_dollars", "close"]:
        value = price_block.get(key)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except Exception:
            continue

    return None


def parse_candles(json_path):
    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    parsed = []
    for candle in data.get("candlesticks", []):
        end_period_ts = candle.get("end_period_ts")
        close_probability = extract_close_probability(candle)

        if end_period_ts is None or close_probability is None:
            continue

        try:
            parsed.append((int(end_period_ts), float(close_probability)))
        except Exception:
            continue

    parsed.sort(key=lambda item: item[0])
    return parsed


def select_closest_candle(candles, close_ts, target_ts, tolerance_seconds):
    eligible = [candle for candle in candles if candle[0] <= close_ts]
    if len(eligible) == 0:
        return None

    closest = min(eligible, key=lambda item: abs(item[0] - target_ts))
    if abs(closest[0] - target_ts) > tolerance_seconds:
        return None
    return closest


def select_last_preclose_candle(candles, close_ts):
    eligible = [candle for candle in candles if candle[0] <= close_ts]
    if len(eligible) == 0:
        return None
    return eligible[-1]


def main():
    sample_df = pd.read_csv(SAMPLE_PATH, low_memory=False)
    sample_df["close_time"] = pd.to_datetime(sample_df["close_time"], errors="coerce", utc=True)

    rows = []

    for _, row in sample_df.iterrows():
        ticker = row["ticker"]
        json_path = CANDLE_DIR / f"{ticker}.json"

        if not json_path.exists():
            continue

        close_time = pd.to_datetime(row["close_time"], errors="coerce", utc=True)
        if pd.isna(close_time):
            continue

        close_ts = int(close_time.timestamp())
        candles = parse_candles(json_path)

        for label, delta, tolerance_seconds in TIMEPOINTS:
            target_ts = int((close_time - delta).timestamp())
            selected = select_closest_candle(
                candles=candles,
                close_ts=close_ts,
                target_ts=target_ts,
                tolerance_seconds=tolerance_seconds,
            )

            rows.append(
                {
                    "ticker": ticker,
                    "title": row.get("title"),
                    "result": row.get("result"),
                    "outcome": row.get("outcome"),
                    "resolution_month": row.get("resolution_month"),
                    "liquidity_bucket": row.get("liquidity_bucket"),
                    "timepoint": label,
                    "target_ts": target_ts,
                    "candle_end_ts": selected[0] if selected else None,
                    "time_diff_seconds": abs(selected[0] - target_ts) if selected else None,
                    "implied_prob": selected[1] if selected else None,
                    "matched": selected is not None,
                }
            )

        last_preclose = select_last_preclose_candle(candles=candles, close_ts=close_ts)
        rows.append(
            {
                "ticker": ticker,
                "title": row.get("title"),
                "result": row.get("result"),
                "outcome": row.get("outcome"),
                "resolution_month": row.get("resolution_month"),
                "liquidity_bucket": row.get("liquidity_bucket"),
                "timepoint": "last_preclose",
                "target_ts": close_ts,
                "candle_end_ts": last_preclose[0] if last_preclose else None,
                "time_diff_seconds": abs(last_preclose[0] - close_ts) if last_preclose else None,
                "implied_prob": last_preclose[1] if last_preclose else None,
                "matched": last_preclose is not None,
            }
        )

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUTPUT_PATH, index=False)

    print("Done extracting event-time probabilities.")
    print("Rows written:", len(out_df))
    print("Matched rows:", int(out_df["matched"].sum()) if len(out_df) > 0 else 0)
    print(f"Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
