import json
import time
from pathlib import Path

import pandas as pd
import requests
from requests import HTTPError

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
CUTOFF_URL = f"{BASE_URL}/historical/cutoff"
HISTORICAL_CANDLE_URL = f"{BASE_URL}/historical/markets/{{ticker}}/candlesticks"
LIVE_BATCH_CANDLE_URL = f"{BASE_URL}/markets/candlesticks"

INPUT_PATH = Path("data/processed/event_time_stratified_sample.csv")
OUTPUT_DIR = Path("data/raw/event_time_sample_candles")
SUMMARY_PATH = Path("data/processed/event_time_sample_candle_download_summary.csv")
PERIOD_INTERVAL = 60
BASE_SLEEP_SECONDS = 0.2
MAX_RETRIES = 5
LOOKBACK_BUFFER = pd.Timedelta(days=3)


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


def load_existing_summary():
    if not SUMMARY_PATH.exists():
        return {}

    summary_df = pd.read_csv(SUMMARY_PATH, low_memory=False)
    if "ticker" not in summary_df.columns:
        return {}

    return {
        row["ticker"]: row.to_dict()
        for _, row in summary_df.iterrows()
    }


def write_summary_rows(summary_rows):
    summary_by_ticker = {}
    for row in summary_rows:
        summary_by_ticker[row["ticker"]] = row

    ordered_rows = [summary_by_ticker[ticker] for ticker in sorted(summary_by_ticker)]
    pd.DataFrame(ordered_rows).to_csv(SUMMARY_PATH, index=False)


def count_existing_candles(output_path):
    with open(output_path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    return len(payload.get("candlesticks", []))


def request_with_retries(session, url, params):
    delay = 1.0

    for attempt in range(1, MAX_RETRIES + 1):
        response = session.get(url, params=params, timeout=30)

        try:
            response.raise_for_status()
            return response
        except HTTPError:
            if response.status_code != 429 or attempt == MAX_RETRIES:
                raise

            print(
                f"Rate limited on attempt {attempt}/{MAX_RETRIES}; "
                f"sleeping {delay:.1f}s before retry."
            )
            time.sleep(delay)
            delay *= 2

    raise RuntimeError("Exceeded retry attempts while fetching candlesticks")


def main():
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], errors="coerce", utc=True)
    sample_tickers = set(df["ticker"])

    cutoff_response = requests.get(CUTOFF_URL, timeout=30)
    cutoff_response.raise_for_status()
    cutoff_data = cutoff_response.json()
    cutoff_ts = int(pd.to_datetime(cutoff_data["market_settled_ts"], utc=True).timestamp())

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    existing_summary = {
        ticker: row
        for ticker, row in load_existing_summary().items()
        if ticker in sample_tickers
    }
    summary_rows = list(existing_summary.values())
    success_count = 0
    fail_count = 0

    if existing_summary:
        for row in existing_summary.values():
            if bool(row.get("success")):
                success_count += 1
            else:
                fail_count += 1

    for idx, row in df.iterrows():
        ticker = row["ticker"]
        output_path = OUTPUT_DIR / f"{ticker}.json"

        if ticker in existing_summary and output_path.exists():
            print(f"[{idx + 1}/{len(df)}] Reusing existing file for {ticker}")
            continue

        if pd.isna(row["open_time"]) or pd.isna(row["close_time"]):
            fail_count += 1
            summary_rows.append({
                "ticker": ticker,
                "endpoint_type": "missing_time",
                "success": False,
                "candlestick_count": 0,
                "error": "missing open_time or close_time",
            })
            write_summary_rows(summary_rows)
            print(f"[{idx + 1}/{len(df)}] Skipping {ticker}: missing open_time/close_time")
            continue

        fetch_start_time = max(row["open_time"], row["close_time"] - LOOKBACK_BUFFER)
        start_ts = to_unix_timestamp(fetch_start_time)
        end_ts = to_unix_timestamp(row["close_time"])
        endpoint_type = pick_endpoint(row, cutoff_ts)

        try:
            if output_path.exists():
                candlestick_count = count_existing_candles(output_path)
                success_count += 1
                summary_rows.append({
                    "ticker": ticker,
                    "endpoint_type": endpoint_type,
                    "success": True,
                    "candlestick_count": candlestick_count,
                    "error": "",
                })
                write_summary_rows(summary_rows)
                print(
                    f"[{idx + 1}/{len(df)}] Reusing existing file with "
                    f"{candlestick_count} candles for {ticker}"
                )
                continue

            if endpoint_type == "historical":
                response = request_with_retries(
                    session,
                    HISTORICAL_CANDLE_URL.format(ticker=ticker),
                    params={
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "period_interval": PERIOD_INTERVAL,
                    },
                )
                payload = response.json()
            else:
                response = request_with_retries(
                    session,
                    LIVE_BATCH_CANDLE_URL,
                    params={
                        "market_tickers": ticker,
                        "start_ts": start_ts,
                        "end_ts": end_ts,
                        "period_interval": PERIOD_INTERVAL,
                    },
                )
                payload = normalize_live_candle_response(ticker, response.json())

            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, indent=2)

            candlestick_count = len(payload.get("candlesticks", []))
            success_count += 1
            summary_rows.append({
                "ticker": ticker,
                "endpoint_type": endpoint_type,
                "success": True,
                "candlestick_count": candlestick_count,
                "error": "",
            })
            write_summary_rows(summary_rows)
            print(
                f"[{idx + 1}/{len(df)}] Saved {candlestick_count} candles for "
                f"{ticker} via {endpoint_type}"
            )
        except Exception as error:
            fail_count += 1
            summary_rows.append({
                "ticker": ticker,
                "endpoint_type": endpoint_type,
                "success": False,
                "candlestick_count": 0,
                "error": str(error),
            })
            write_summary_rows(summary_rows)
            print(f"[{idx + 1}/{len(df)}] Failed for {ticker}: {error}")

        time.sleep(BASE_SLEEP_SECONDS)

    write_summary_rows(summary_rows)

    print()
    print("Finished downloading event-time sample candles.")
    print("Success count:", success_count)
    print("Fail count:", fail_count)
    print(f"Saved summaries to: {SUMMARY_PATH}")
    print(f"Saved candle files to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
