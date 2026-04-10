import argparse
import csv
import json
import sqlite3
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
CUTOFF_URL = f"{BASE_URL}/historical/cutoff"
HISTORICAL_MARKETS_URL = f"{BASE_URL}/historical/markets"
LIVE_MARKETS_URL = f"{BASE_URL}/markets"

OUTPUT_PATH = Path("data/processed/event_time_universe.csv")
STATS_PATH = Path("data/processed/event_time_universe_build_stats.json")
SCAN_DB_PATH = Path("data/processed/.event_time_metadata_scan.sqlite")

FIELDNAMES = [
    "ticker",
    "title",
    "event_ticker",
    "market_type",
    "status",
    "result",
    "outcome",
    "created_time",
    "open_time",
    "close_time",
    "settlement_ts",
    "volume_fp",
    "liquidity_dollars",
    "open_interest_fp",
    "resolution_month",
    "source",
]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2025-04-01")
    parser.add_argument("--end-date", default="2026-03-31")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--max-historical-pages", type=int, default=None)
    parser.add_argument("--max-live-pages", type=int, default=None)
    return parser.parse_args()


def normalize_time_text(value):
    if value in [None, ""]:
        return None
    if not isinstance(value, str):
        value = str(value)
    return value


def date_prefix(value):
    normalized = normalize_time_text(value)
    if normalized is None or len(normalized) < 10:
        return None
    return normalized[:10]


def outcome_from_result(result_text):
    if result_text == "yes":
        return 1
    if result_text == "no":
        return 0
    return None


def market_in_window(market, start_date, end_date):
    close_date = date_prefix(market.get("close_time"))
    settlement_date = date_prefix(market.get("settlement_ts"))

    for candidate_date in [close_date, settlement_date]:
        if candidate_date is None:
            continue
        if start_date <= candidate_date <= end_date:
            return True

    return False


def market_anchor_ts(market):
    close_date = date_prefix(market.get("close_time"))
    settlement_date = date_prefix(market.get("settlement_ts"))

    for candidate_date in [close_date, settlement_date]:
        if candidate_date is not None:
            return candidate_date

    return None


def page_is_entirely_before_window(markets, start_date):
    anchor_dates = [market_anchor_ts(market) for market in markets]
    anchor_dates = [value for value in anchor_dates if value is not None]

    if not anchor_dates:
        return False

    newest_page_date = max(anchor_dates)
    return newest_page_date < start_date


def normalize_market(market, source):
    close_time = normalize_time_text(market.get("close_time"))

    resolution_month = None
    if close_time is not None and len(close_time) >= 7:
        resolution_month = close_time[:7]

    result_text = market.get("result")

    return {
        "ticker": market.get("ticker"),
        "title": market.get("title"),
        "event_ticker": market.get("event_ticker"),
        "market_type": market.get("market_type"),
        "status": market.get("status"),
        "result": result_text,
        "outcome": outcome_from_result(result_text),
        "created_time": normalize_time_text(market.get("created_time")),
        "open_time": normalize_time_text(market.get("open_time")),
        "close_time": close_time,
        "settlement_ts": normalize_time_text(market.get("settlement_ts")),
        "volume_fp": market.get("volume_fp"),
        "liquidity_dollars": market.get("liquidity_dollars"),
        "open_interest_fp": market.get("open_interest_fp"),
        "resolution_month": resolution_month,
        "source": source,
    }


def create_scan_tracker():
    if SCAN_DB_PATH.exists():
        SCAN_DB_PATH.unlink()

    connection = sqlite3.connect(SCAN_DB_PATH)
    connection.execute("PRAGMA journal_mode = OFF")
    connection.execute("PRAGMA synchronous = OFF")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS scanned_tickers (
            ticker TEXT PRIMARY KEY
        )
        """
    )
    connection.commit()
    return connection


def track_scanned_tickers(connection, markets):
    ticker_rows = []
    for market in markets:
        ticker = market.get("ticker")
        if ticker:
            ticker_rows.append((ticker,))

    if not ticker_rows:
        return

    connection.executemany(
        "INSERT OR IGNORE INTO scanned_tickers (ticker) VALUES (?)",
        ticker_rows,
    )
    connection.commit()


def count_scanned_tickers(connection):
    return int(connection.execute("SELECT COUNT(*) FROM scanned_tickers").fetchone()[0])


def remove_scan_tracker(connection):
    connection.close()
    if SCAN_DB_PATH.exists():
        SCAN_DB_PATH.unlink()


def stream_historical_markets(writer, start_date, end_date, limit, max_pages, scan_tracker):
    session = requests.Session()
    cursor = None
    page_number = 1
    pages_fetched = 0
    rows_scanned = 0
    rows_written = 0

    while True:
        params = {
            "limit": limit,
            "mve_filter": "exclude",
        }
        if cursor:
            params["cursor"] = cursor

        response = session.get(HISTORICAL_MARKETS_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        markets = data.get("markets", [])
        cursor = data.get("cursor")
        pages_fetched += 1

        rows_scanned += len(markets)
        track_scanned_tickers(scan_tracker, markets)

        for market in markets:
            if not market_in_window(market, start_date, end_date):
                continue
            writer.writerow(normalize_market(market, "historical"))
            rows_written += 1

        print(
            f"Historical page {page_number}: scanned {len(markets)} "
            f"markets, kept {rows_written} total"
        )

        if page_is_entirely_before_window(markets, start_date):
            print(
                "Historical scan reached pages entirely before the start window; "
                "stopping early."
            )
            break

        if not cursor:
            break

        if max_pages is not None and pages_fetched >= max_pages:
            break
        page_number += 1

    return {
        "pages_fetched": pages_fetched,
        "rows_scanned": rows_scanned,
        "rows_written": rows_written,
    }


def stream_live_markets(writer, min_settled_ts, max_settled_ts, limit, max_pages, scan_tracker):
    session = requests.Session()
    cursor = None
    page_number = 1
    pages_fetched = 0
    rows_scanned = 0
    rows_written = 0

    while True:
        params = {
            "limit": limit,
            "status": "settled",
            "min_settled_ts": min_settled_ts,
            "max_settled_ts": max_settled_ts,
            "mve_filter": "exclude",
        }
        if cursor:
            params["cursor"] = cursor

        response = session.get(LIVE_MARKETS_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        markets = data.get("markets", [])
        cursor = data.get("cursor")
        pages_fetched += 1

        rows_scanned += len(markets)
        track_scanned_tickers(scan_tracker, markets)

        for market in markets:
            writer.writerow(normalize_market(market, "live"))
            rows_written += 1

        print(
            f"Live page {page_number}: scanned {len(markets)} "
            f"markets, kept {rows_written} total"
        )

        if not cursor:
            break

        if max_pages is not None and pages_fetched >= max_pages:
            break
        page_number += 1

    return {
        "pages_fetched": pages_fetched,
        "rows_scanned": rows_scanned,
        "rows_written": rows_written,
    }


def main():
    args = parse_args()

    start_date = args.start_date
    end_date = args.end_date
    start_ts = int(pd.Timestamp(args.start_date, tz="UTC").timestamp())
    end_ts_exclusive = int(
        (pd.Timestamp(args.end_date, tz="UTC") + pd.Timedelta(days=1)).timestamp()
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    cutoff_response = requests.get(CUTOFF_URL, timeout=30)
    cutoff_response.raise_for_status()
    cutoff_data = cutoff_response.json()
    market_cutoff_ts = int(
        pd.to_datetime(cutoff_data["market_settled_ts"], utc=True).timestamp()
    )

    live_min_settled_ts = max(start_ts, market_cutoff_ts)
    live_max_settled_ts = end_ts_exclusive

    scan_tracker = create_scan_tracker()

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()

        historical_stats = stream_historical_markets(
            writer,
            start_date=start_date,
            end_date=end_date,
            limit=args.limit,
            max_pages=args.max_historical_pages,
            scan_tracker=scan_tracker,
        )

        live_stats = stream_live_markets(
            writer,
            min_settled_ts=live_min_settled_ts,
            max_settled_ts=live_max_settled_ts,
            limit=args.limit,
            max_pages=args.max_live_pages,
            scan_tracker=scan_tracker,
        )

    unique_markets_pulled_from_metadata = count_scanned_tickers(scan_tracker)
    remove_scan_tracker(scan_tracker)

    universe_df = pd.read_csv(OUTPUT_PATH, low_memory=False)
    universe_df = universe_df.drop_duplicates(subset=["ticker"]).copy()
    universe_df.to_csv(OUTPUT_PATH, index=False)

    stats = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "historical_cutoff_market_settled_ts": cutoff_data["market_settled_ts"],
        "historical": historical_stats,
        "live": live_stats,
        "raw_markets_scanned_total": (
            historical_stats["rows_scanned"] + live_stats["rows_scanned"]
        ),
        "unique_markets_pulled_from_metadata": unique_markets_pulled_from_metadata,
        "date_window_universe_count": int(len(universe_df)),
    }

    with open(STATS_PATH, "w", encoding="utf-8") as file:
        json.dump(stats, file, indent=2)

    print()
    print("Done building event-time universe.")
    print("Universe rows saved:", len(universe_df))
    print("Historical cutoff:", cutoff_data["market_settled_ts"])
    print(f"Saved universe to: {OUTPUT_PATH}")
    print(f"Saved build stats to: {STATS_PATH}")


if __name__ == "__main__":
    main()
