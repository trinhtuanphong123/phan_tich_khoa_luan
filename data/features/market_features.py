from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from data.market.repository import get_daily_ohlcv


ROLLING_WINDOW_DAYS = 5


def _to_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _normalize_symbols(symbols: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted({symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()})


def _build_value_matrix(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_date: date | datetime | str,
    end_date: date | datetime | str,
    value_column: str,
) -> pd.DataFrame:
    normalized_symbols = _normalize_symbols(symbols)
    if not normalized_symbols:
        return pd.DataFrame()

    daily = get_daily_ohlcv(normalized_symbols, start_date, end_date)
    if daily.empty:
        return pd.DataFrame(columns=normalized_symbols)

    daily = daily.copy()
    daily["trade_date"] = pd.to_datetime(daily["trade_date"], errors="coerce")
    matrix = (
        daily.pivot_table(index="trade_date", columns="symbol", values=value_column, aggfunc="last")
        .sort_index()
        .reindex(columns=normalized_symbols)
    )
    matrix.index.name = "trade_date"
    return matrix


def build_close_matrix(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_date: date | datetime | str,
    end_date: date | datetime | str,
) -> pd.DataFrame:
    return _build_value_matrix(symbols, start_date, end_date, "close")


def build_return_matrix(close_matrix: pd.DataFrame) -> pd.DataFrame:
    if close_matrix.empty:
        return close_matrix.copy()
    return np.log(close_matrix / close_matrix.shift(1))


def build_market_feature_matrix(
    symbols: list[str] | tuple[str, ...] | set[str],
    end_date: date | datetime | str,
    lookback_days: int,
) -> pd.DataFrame:
    resolved_end_date = _to_date(end_date)
    resolved_start_date = resolved_end_date - timedelta(days=lookback_days - 1)

    close_matrix = build_close_matrix(symbols, resolved_start_date, resolved_end_date)
    if close_matrix.empty:
        return pd.DataFrame()

    volume_matrix = _build_value_matrix(symbols, resolved_start_date, resolved_end_date, "volume")
    log_return_matrix = build_return_matrix(close_matrix)
    rolling_return_matrix = close_matrix / close_matrix.shift(ROLLING_WINDOW_DAYS) - 1.0
    rolling_volatility_matrix = log_return_matrix.rolling(ROLLING_WINDOW_DAYS).std()
    volume_change_matrix = volume_matrix.pct_change()
    liquidity_proxy_matrix = close_matrix * volume_matrix

    feature_frames = {
        "close": close_matrix,
        "log_return": log_return_matrix,
        "rolling_return": rolling_return_matrix,
        "rolling_volatility": rolling_volatility_matrix,
        "volume_change": volume_change_matrix,
        "liquidity_proxy": liquidity_proxy_matrix,
    }

    combined = pd.concat(feature_frames, axis=1)
    combined.index.name = "trade_date"
    return combined.sort_index(axis=1)
