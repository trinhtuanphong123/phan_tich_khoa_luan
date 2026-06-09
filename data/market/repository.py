from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from data.storage import market_repo


def get_ohlcv_5m(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_ts: datetime | str,
    end_ts: datetime | str,
) -> pd.DataFrame:
    return market_repo.get_ohlcv_5m(symbols, start_ts, end_ts)


def get_daily_ohlcv(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_date: date | datetime | str,
    end_date: date | datetime | str,
) -> pd.DataFrame:
    return market_repo.get_daily_ohlcv(symbols, start_date, end_date)


def get_latest_bar_time(symbol: str, interval: str) -> pd.Timestamp | None:
    return market_repo.get_latest_bar_time(symbol, interval)


def find_missing_bars(
    symbol: str,
    expected_timestamps: list[datetime | str],
    interval: str,
) -> list[pd.Timestamp]:
    return market_repo.find_missing_bars(symbol, expected_timestamps, interval)
