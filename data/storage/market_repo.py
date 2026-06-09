from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from data.market.calendar import VN_TIMEZONE

from .models import MarketOHLCV1d, MarketOHLCV5m, SessionLocal


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _to_vn_timestamp(value: datetime | str | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(VN_TIMEZONE)
    return timestamp.tz_convert(VN_TIMEZONE)


def _to_trade_date(value: date | datetime | str | pd.Timestamp) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return _to_vn_timestamp(value).date()


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _normalize_market_rows(
    rows: pd.DataFrame | list[dict[str, object]],
    *,
    interval: str,
) -> pd.DataFrame:
    frame = _to_dataframe(rows)
    if frame.empty:
        return frame

    frame = frame.copy()
    frame["symbol"] = frame["symbol"].astype("string").str.upper()
    if "source" not in frame.columns:
        frame["source"] = "vnstock"
    else:
        frame["source"] = frame["source"].fillna("vnstock").astype("string")
    if "fetched_at" not in frame.columns:
        frame["fetched_at"] = datetime.now(VN_TIMEZONE)
    else:
        frame["fetched_at"] = pd.to_datetime(frame["fetched_at"], errors="coerce").fillna(pd.Timestamp.now(tz=VN_TIMEZONE))

    if interval == "1d":
        if "trade_date" not in frame.columns:
            frame["trade_date"] = frame["ts"].map(_to_trade_date) if "ts" in frame.columns else frame["date"].map(_to_trade_date)
        frame["trade_date"] = frame["trade_date"].map(_to_trade_date)
        if "ts" not in frame.columns:
            if "date" in frame.columns:
                frame["ts"] = frame["date"].map(_to_vn_timestamp)
            else:
                frame["ts"] = frame["trade_date"].map(lambda value: pd.Timestamp(value).tz_localize(VN_TIMEZONE))
        else:
            frame["ts"] = frame["ts"].map(_to_vn_timestamp)
    else:
        frame["ts"] = frame["ts"].map(_to_vn_timestamp)
        if "trade_date" not in frame.columns:
            frame["trade_date"] = frame["ts"].map(lambda value: value.date())
        else:
            frame["trade_date"] = frame["trade_date"].map(_to_trade_date)

    for column in ["open", "high", "low", "close", "volume", "value"]:
        if column not in frame.columns:
            frame[column] = None
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    if interval == "1d":
        for column in ["buy_foreign", "sell_foreign"]:
            if column not in frame.columns:
                frame[column] = 0
            frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    return frame


def upsert_ohlcv_5m(rows: pd.DataFrame | list[dict[str, object]]) -> int:
    frame = _normalize_market_rows(rows, interval="5m")
    if frame.empty:
        return 0

    session = SessionLocal()
    try:
        count = 0
        for _, row in frame.iterrows():
            existing = (
                session.query(MarketOHLCV5m)
                .filter(
                    MarketOHLCV5m.symbol == row["symbol"],
                    MarketOHLCV5m.ts == row["ts"].to_pydatetime(),
                    MarketOHLCV5m.source == str(row["source"]),
                )
                .first()
            )
            payload = {
                "symbol": row["symbol"],
                "ts": row["ts"].to_pydatetime(),
                "trade_date": row["trade_date"],
                "open": None if pd.isna(row["open"]) else float(row["open"]),
                "high": None if pd.isna(row["high"]) else float(row["high"]),
                "low": None if pd.isna(row["low"]) else float(row["low"]),
                "close": None if pd.isna(row["close"]) else float(row["close"]),
                "volume": None if pd.isna(row["volume"]) else int(row["volume"]),
                "value": None if pd.isna(row["value"]) else float(row["value"]),
                "source": str(row["source"]),
                "fetched_at": pd.Timestamp(row["fetched_at"]).to_pydatetime(),
            }
            if existing is None:
                session.add(MarketOHLCV5m(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            count += 1
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upsert_ohlcv_1d(rows: pd.DataFrame | list[dict[str, object]]) -> int:
    frame = _normalize_market_rows(rows, interval="1d")
    if frame.empty:
        return 0

    session = SessionLocal()
    try:
        count = 0
        for _, row in frame.iterrows():
            existing = (
                session.query(MarketOHLCV1d)
                .filter(
                    MarketOHLCV1d.symbol == row["symbol"],
                    MarketOHLCV1d.trade_date == row["trade_date"],
                    MarketOHLCV1d.source == str(row["source"]),
                )
                .first()
            )
            payload = {
                "symbol": row["symbol"],
                "ts": row["ts"].to_pydatetime(),
                "trade_date": row["trade_date"],
                "open": None if pd.isna(row["open"]) else float(row["open"]),
                "high": None if pd.isna(row["high"]) else float(row["high"]),
                "low": None if pd.isna(row["low"]) else float(row["low"]),
                "close": None if pd.isna(row["close"]) else float(row["close"]),
                "volume": None if pd.isna(row["volume"]) else int(row["volume"]),
                "value": None if pd.isna(row["value"]) else float(row["value"]),
                "source": str(row["source"]),
                "fetched_at": pd.Timestamp(row["fetched_at"]).to_pydatetime(),
                "buy_foreign": int(row["buy_foreign"]) if not pd.isna(row["buy_foreign"]) else 0,
                "sell_foreign": int(row["sell_foreign"]) if not pd.isna(row["sell_foreign"]) else 0,
            }
            if existing is None:
                session.add(MarketOHLCV1d(**payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            count += 1
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_ohlcv_5m(symbols: list[str] | tuple[str, ...] | set[str], start_ts: datetime | str, end_ts: datetime | str) -> pd.DataFrame:
    normalized_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()})
    if not normalized_symbols:
        return pd.DataFrame()

    start_value = _to_vn_timestamp(start_ts).to_pydatetime()
    end_value = _to_vn_timestamp(end_ts).to_pydatetime()

    session = SessionLocal()
    try:
        rows = (
                session.query(MarketOHLCV5m)
                .filter(
                MarketOHLCV5m.symbol.in_(normalized_symbols),
                MarketOHLCV5m.ts >= start_value,
                MarketOHLCV5m.ts <= end_value,
            )
            .order_by(MarketOHLCV5m.symbol.asc(), MarketOHLCV5m.ts.asc())
            .all()
        )
    finally:
        session.close()

    return pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "ts": _to_vn_timestamp(row.ts),
                "trade_date": row.trade_date,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "value": row.value,
                "source": row.source,
                "fetched_at": row.fetched_at,
            }
            for row in rows
        ]
    )


def get_ohlcv_1d(symbols: list[str] | tuple[str, ...] | set[str], start_date: date | datetime | str, end_date: date | datetime | str) -> pd.DataFrame:
    normalized_symbols = sorted({symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()})
    if not normalized_symbols:
        return pd.DataFrame()

    start_value = _to_trade_date(start_date)
    end_value = _to_trade_date(end_date)

    session = SessionLocal()
    try:
        rows = (
                session.query(MarketOHLCV1d)
                .filter(
                MarketOHLCV1d.symbol.in_(normalized_symbols),
                MarketOHLCV1d.trade_date >= start_value,
                MarketOHLCV1d.trade_date <= end_value,
            )
            .order_by(MarketOHLCV1d.symbol.asc(), MarketOHLCV1d.trade_date.asc())
            .all()
        )
    finally:
        session.close()

    return pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "ts": _to_vn_timestamp(row.ts),
                "trade_date": row.trade_date,
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
                "value": row.value,
                "source": row.source,
                "fetched_at": row.fetched_at,
                "buy_foreign": row.buy_foreign,
                "sell_foreign": row.sell_foreign,
            }
            for row in rows
        ]
    )


def get_latest_timestamp(symbol: str, interval: str) -> pd.Timestamp | None:
    normalized_symbol = _normalize_symbol(symbol)
    session = SessionLocal()
    try:
        if interval == "1d":
            row = (
                session.query(MarketOHLCV1d.ts)
                .filter(MarketOHLCV1d.symbol == normalized_symbol)
                .order_by(MarketOHLCV1d.ts.desc())
                .first()
            )
        else:
            row = (
                session.query(MarketOHLCV5m.ts)
                .filter(MarketOHLCV5m.symbol == normalized_symbol)
                .order_by(MarketOHLCV5m.ts.desc())
                .first()
            )
    finally:
        session.close()

    if row is None:
        return None
    return _to_vn_timestamp(row[0])


def find_missing_bars(symbol: str, expected_timestamps: list[datetime | str], interval: str) -> list[pd.Timestamp]:
    expected = [_to_vn_timestamp(value) for value in expected_timestamps]
    if not expected:
        return []

    if interval == "1d":
        frame = get_ohlcv_1d([symbol], min(expected), max(expected))
    else:
        frame = get_ohlcv_5m([symbol], min(expected), max(expected))

    if frame.empty:
        return expected

    actual = {_to_vn_timestamp(value) for value in frame["ts"].tolist() if not pd.isna(value)}
    return [timestamp for timestamp in expected if timestamp not in actual]


def get_daily_ohlcv(symbols: list[str] | tuple[str, ...] | set[str], start_date: date | datetime | str, end_date: date | datetime | str) -> pd.DataFrame:
    return get_ohlcv_1d(symbols, start_date, end_date)


def get_latest_bar_time(symbol: str, interval: str) -> pd.Timestamp | None:
    return get_latest_timestamp(symbol, interval)


def get_existing_trade_dates(symbol: str, start_date: date | datetime | str, end_date: date | datetime | str) -> set[date]:
    normalized_symbol = _normalize_symbol(symbol)
    start_value = _to_trade_date(start_date)
    end_value = _to_trade_date(end_date)

    session = SessionLocal()
    try:
        rows = (
            session.query(MarketOHLCV1d.trade_date)
            .filter(
                MarketOHLCV1d.symbol == normalized_symbol,
                MarketOHLCV1d.trade_date >= start_value,
                MarketOHLCV1d.trade_date <= end_value,
            )
            .all()
        )
    finally:
        session.close()

    return {row[0] for row in rows}


def delete_ohlcv_1d(symbol: str) -> int:
    normalized_symbol = _normalize_symbol(symbol)

    session = SessionLocal()
    try:
        deleted_count = (
            session.query(MarketOHLCV1d)
            .filter(MarketOHLCV1d.symbol == normalized_symbol)
            .delete(synchronize_session=False)
        )
        session.commit()
        return int(deleted_count)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
