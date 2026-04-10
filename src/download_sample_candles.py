import json
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
CUTOFF_URL = f"{BASE_URL}/historical/cutoff"
HISTORICAL_CANDLE_URL = f"{BASE_URL}/historical/markets/{{ticker}}/candlesticks"
LIVE_BATCH_CANDLE_URL = f"{BASE_URL}/markets/candlesticks"

INPUT_PATH = Path("data/processed/event_time_stratified_sample.csv")
OUTPUT_DIR = Path("data/raw/event_time_sample_candles")
SUMMARY_PATH = Path("data/processed/event_time_sample_candle_download_summary.csv")
PERIOD_INTERVAL = 60


def to_unix_timestamp(value):
    return int(pd.Timestamp(value).timestamp())


def pick_endpoint(row, cutoff_ts):
    settlement_ts = pd.to_datetime(row["settlement_ts"], errors="coerce", utc=True)
    close_time = pd.to_datetime(row["close_time"], errors="coerce", utc=True)

    comparison_ts = settlement_ts
    if pd.isna(comparison_ts):
        comparison_ts = close_time

    if pd.isna(comparison_ts):
        return None

    if int(comparison_ts.timestamp()) < cutoff_ts:
        return "historical"
    return "live"


def normalize_live_candle_response(ticker, data):
    markets = data.get("markets", [])
    if len(markets) == 0:
        return {
            "ticker": ticker,
            "candlesticks": [],
        }

    return {
        "ticker": ticker,
        "candlesticks": markets[0].get("candlesticks", []),
    }


def main():
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], errors="coerce", utc=True)

    cutoff_response = requests.get(CUTOFF_URL, timeout=30)
    cutoff_response.raise_for_status()
    cutoff_data = cutoff_response.json()
    cutoff_ts = int(pd.to_datetime(cutoff_data["market_settled_ts"], utc=True).timestamp())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    summary_rows = []
    success_count = 0
    fail_count = 0

    for idx, row in df.iterrows():
        ticker = row["ticker"]
        output_path = OUTPUT_DIR / f"{ticker}.json"

        if pd.isna(row["open_time"]) or pd.isna(row["close_time"]):
            fail_count += 1
            summary_rows.append(
                {
                    "ticker": ticker,
                    "endpoint_type": "missing_time",
                    "success": False,
                    "candlestick_count": 0,
                    "error": "missing open_time or close_time",
                }
            )
            print(f"[{idx + 1}/{len(df)}] Skipping {ticker}: missing open_time/close_time")
            continue

        start_ts = to_unix_timestamp(row["open_time"])
        end_ts = to_unix_timestamp(row["close_time"])
        endpoint_type = pick_endpoint(row, cutoff_ts)

        try:
            if endpoint_type == "historical":
                response = session.get(
                    HISTORICAL_CANDLE_URL.format(ticker=ticker),
                    params={
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "period_interval": PERIOD_INTERVAL,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
            else:
                response = session.get(
                    LIVE_BATCH_CANDLE_URL,
                    params={
                        "market_tickers": ticker,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "period_interval": PERIOD_INTERVAL,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                payload = normalize_live_candle_response(ticker, response.json())

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)

            candlestick_count = len(payload.get("candlesticks", []))
            success_count += 1
            summary_rows.append(
                {
                    "ticker": ticker,
                    "endpoint_type": endpoint_type,
                    "success": True,
                    "candlestick_count": candlestick_count,
                    "error": "",
                }
            )
            print(
                f"[{idx + 1}/{len(df)}] Saved {candlestick_count} candles for "
                f"{ticker} via {endpoint_type}"
            )
        except Exception as error:
            fail_count += 1
            summary_rows.append(
                {
                    "ticker": ticker,
                    "endpoint_type": endpoint_type,
                    "success": False,
                    "candlestick_count": 0,
                    "error": str(error),
                }
            )
            print(f"[{idx + 1}/{len(df)}] Failed for {ticker}: {error}")

        time.sleep(0.05)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(SUMMARY_PATH, index=False)

    print()
    print("Finished downloading event-time sample candles.")
    print("Success count:", success_count)
    print("Fail count:", fail_count)
    print(f"Saved summaries to: {SUMMARY_PATH}")
    print(f"Saved candle files to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
