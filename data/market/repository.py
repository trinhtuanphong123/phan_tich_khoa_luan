from __future__ import annotations

from datetime import date, datetime
from typing import Any

import pandas as pd

from data.market.calendar import VN_TIMEZONE
from data.storage import market_repo
from data.storage.models import MarketDataDaily, MarketDataIntraday, SessionLocal


def _normalize_symbols(symbols: list[str] | tuple[str, ...] | set[str]) -> list[str]:
    return sorted({symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()})


def _to_vn_timestamp(value: datetime | str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(VN_TIMEZONE)
    return timestamp.tz_convert(VN_TIMEZONE)


def _to_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


def _maybe_delegate(function_name: str, *args: Any) -> Any:
    function = getattr(market_repo, function_name, None)
    if callable(function):
        return function(*args)
    return None


def get_ohlcv_5m(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_ts: datetime | str,
    end_ts: datetime | str,
) -> pd.DataFrame:
    delegated = _maybe_delegate("get_ohlcv_5m", symbols, start_ts, end_ts)
    if delegated is not None:
        return delegated

    normalized_symbols = _normalize_symbols(symbols)
    if not normalized_symbols:
        return pd.DataFrame(
            columns=["symbol", "ts", "trade_date", "open", "high", "low", "close", "volume"]
        )

    start_value = _to_vn_timestamp(start_ts).to_pydatetime()
    end_value = _to_vn_timestamp(end_ts).to_pydatetime()

    session = SessionLocal()
    try:
        rows = (
            session.query(MarketDataIntraday)
            .filter(
                MarketDataIntraday.ticker.in_(normalized_symbols),
                MarketDataIntraday.timestamp >= start_value,
                MarketDataIntraday.timestamp <= end_value,
            )
            .order_by(MarketDataIntraday.ticker.asc(), MarketDataIntraday.timestamp.asc())
            .all()
        )
    finally:
        session.close()

    records = [
        {
            "symbol": row.ticker,
            "ts": _to_vn_timestamp(row.timestamp),
            "trade_date": _to_vn_timestamp(row.timestamp).date(),
            "open": row.price,
            "high": row.price,
            "low": row.price,
            "close": row.price,
            "volume": row.volume,
        }
        for row in rows
    ]
    return pd.DataFrame(records)


def get_daily_ohlcv(
    symbols: list[str] | tuple[str, ...] | set[str],
    start_date: date | datetime | str,
    end_date: date | datetime | str,
) -> pd.DataFrame:
    delegated = _maybe_delegate("get_daily_ohlcv", symbols, start_date, end_date)
    if delegated is not None:
        return delegated

    normalized_symbols = _normalize_symbols(symbols)
    if not normalized_symbols:
        return pd.DataFrame(
            columns=["symbol", "ts", "trade_date", "open", "high", "low", "close", "volume"]
        )

    start_value = _to_date(start_date)
    end_value = _to_date(end_date)

    session = SessionLocal()
    try:
        rows = (
            session.query(MarketDataDaily)
            .filter(
                MarketDataDaily.ticker.in_(normalized_symbols),
                MarketDataDaily.date >= start_value,
                MarketDataDaily.date <= end_value,
            )
            .order_by(MarketDataDaily.ticker.asc(), MarketDataDaily.date.asc())
            .all()
        )
    finally:
        session.close()

    records = [
        {
            "symbol": row.ticker,
            "ts": _to_vn_timestamp(row.date),
            "trade_date": _to_vn_timestamp(row.date).date(),
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        }
        for row in rows
    ]
    return pd.DataFrame(records)


def get_latest_bar_time(symbol: str, interval: str) -> pd.Timestamp | None:
    delegated = _maybe_delegate("get_latest_bar_time", symbol, interval)
    if delegated is not None:
        return delegated

    normalized_symbol = symbol.strip().upper()
    session = SessionLocal()
    try:
        if interval == "1d":
            row = (
                session.query(MarketDataDaily.date)
                .filter(MarketDataDaily.ticker == normalized_symbol)
                .order_by(MarketDataDaily.date.desc())
                .first()
            )
        else:
            row = (
                session.query(MarketDataIntraday.timestamp)
                .filter(MarketDataIntraday.ticker == normalized_symbol)
                .order_by(MarketDataIntraday.timestamp.desc())
                .first()
            )
    finally:
        session.close()

    if row is None:
        return None
    return _to_vn_timestamp(row[0])


def find_missing_bars(
    symbol: str,
    expected_timestamps: list[datetime | str],
    interval: str,
) -> list[pd.Timestamp]:
    delegated = _maybe_delegate("find_missing_bars", symbol, expected_timestamps, interval)
    if delegated is not None:
        return delegated

    expected = [_to_vn_timestamp(value) for value in expected_timestamps]
    if not expected:
        return []

    if interval == "1d":
        frame = get_daily_ohlcv([symbol], min(expected), max(expected))
    else:
        frame = get_ohlcv_5m([symbol], min(expected), max(expected))

    if frame.empty:
        return expected

    actual = {
        _to_vn_timestamp(value)
        for value in frame["ts"].tolist()
        if not pd.isna(value)
    }
    return [timestamp for timestamp in expected if timestamp not in actual]
