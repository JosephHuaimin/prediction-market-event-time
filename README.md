# Prediction Market Event-Time Study

## Overview

This project studies how prediction market prices evolve as resolution approaches. Instead of asking only whether market probabilities are calibrated at a single time, this project asks whether prices become more accurate and separate more clearly by eventual outcome in event time.

The core question is:

> As resolution approaches, do prediction market prices become more accurate and separate more cleanly by eventual outcome?

## Research Design

This repository is designed as a lightweight empirical pipeline:

1. Build a metadata-only universe of resolved binary markets.
2. Filter to markets with valid open and close times in a fixed date window.
3. Draw a stratified sample by resolution month and liquidity bucket.
4. Download candlesticks only for sampled tickers.
5. Extract implied probabilities at fixed time-to-close checkpoints.
6. Evaluate whether prices become more accurate near close and whether eventual Yes/No paths separate.

## Planned Outputs

- `data/processed/event_time_universe.csv`
- `data/processed/event_time_stratified_sample.csv`
- `data/processed/event_time_timepoint_probabilities.csv`
- `data/processed/event_time_metrics_by_timepoint.csv`
- `data/processed/event_time_average_path_by_outcome.csv`
- `data/processed/event_time_sample_construction_table.csv`
- `results/event_time_brier_vs_time.png`
- `results/event_time_average_paths.png`
- `results/event_time_last_preclose_calibration.png`

## Scripts

- `src/build_universe.py`
- `src/draw_stratified_sample.py`
- `src/download_sample_candles.py`
- `src/extract_timepoint_probs.py`
- `src/compute_metrics.py`
- `src/plot_brier_vs_time.py`
- `src/plot_average_paths.py`
- `src/plot_last_preclose_calibration.py`
