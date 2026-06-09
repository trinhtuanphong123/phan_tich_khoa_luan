from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from .models import SessionLocal, StockIndicator


def _to_trade_date(value: date | datetime | str | pd.Timestamp) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return pd.Timestamp(value).date()


def _empty_indicator_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "symbol",
            "trade_date",
            "ema_20",
            "ema_50",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_lower",
            "bb_mid",
            "atr_14",
            "volume_sma_20",
            "updated_at",
        ]
    )


def _normalize_indicator_frame(symbol: str, indicator_df: pd.DataFrame) -> pd.DataFrame:
    if indicator_df.empty:
        return _empty_indicator_frame()

    frame = indicator_df.copy()
    frame["symbol"] = symbol.strip().upper()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date

    for column in [
        "ema_20",
        "ema_50",
        "rsi_14",
        "macd_line",
        "macd_signal",
        "macd_hist",
        "bb_upper",
        "bb_lower",
        "bb_mid",
        "atr_14",
        "volume_sma_20",
    ]:
        if column not in frame.columns:
            frame[column] = None
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["updated_at"] = datetime.utcnow()
    return frame[
        [
            "symbol",
            "trade_date",
            "ema_20",
            "ema_50",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_lower",
            "bb_mid",
            "atr_14",
            "volume_sma_20",
            "updated_at",
        ]
    ].copy()


def save_stock_indicators(symbol: str, indicator_df: pd.DataFrame) -> int:
    frame = _normalize_indicator_frame(symbol, indicator_df)
    if frame.empty:
        return 0

    session = SessionLocal()
    try:
        count = 0
        for _, row in frame.iterrows():
            existing = (
                session.query(StockIndicator)
                .filter(
                    StockIndicator.symbol == row["symbol"],
                    StockIndicator.trade_date == row["trade_date"],
                )
                .first()
            )
            payload = {
                "symbol": row["symbol"],
                "trade_date": row["trade_date"],
                "ema_20": None if pd.isna(row["ema_20"]) else float(row["ema_20"]),
                "ema_50": None if pd.isna(row["ema_50"]) else float(row["ema_50"]),
                "rsi_14": None if pd.isna(row["rsi_14"]) else float(row["rsi_14"]),
                "macd_line": None if pd.isna(row["macd_line"]) else float(row["macd_line"]),
                "macd_signal": None if pd.isna(row["macd_signal"]) else float(row["macd_signal"]),
                "macd_hist": None if pd.isna(row["macd_hist"]) else float(row["macd_hist"]),
                "bb_upper": None if pd.isna(row["bb_upper"]) else float(row["bb_upper"]),
                "bb_lower": None if pd.isna(row["bb_lower"]) else float(row["bb_lower"]),
                "bb_mid": None if pd.isna(row["bb_mid"]) else float(row["bb_mid"]),
                "atr_14": None if pd.isna(row["atr_14"]) else float(row["atr_14"]),
                "volume_sma_20": None if pd.isna(row["volume_sma_20"]) else float(row["volume_sma_20"]),
                "updated_at": row["updated_at"],
            }
            if existing is None:
                session.add(StockIndicator(**payload))
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


def get_stock_indicators(
    symbol: str,
    start_date: date | str | None = None,
    end_date: date | str | None = None,
) -> pd.DataFrame:
    normalized_symbol = symbol.strip().upper()

    session = SessionLocal()
    try:
        query = session.query(StockIndicator).filter(StockIndicator.symbol == normalized_symbol)
        if start_date is not None:
            query = query.filter(StockIndicator.trade_date >= _to_trade_date(start_date))
        if end_date is not None:
            query = query.filter(StockIndicator.trade_date <= _to_trade_date(end_date))
        rows = query.order_by(StockIndicator.trade_date.asc()).all()
    finally:
        session.close()

    if not rows:
        return _empty_indicator_frame()

    return pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "trade_date": row.trade_date,
                "ema_20": row.ema_20,
                "ema_50": row.ema_50,
                "rsi_14": row.rsi_14,
                "macd_line": row.macd_line,
                "macd_signal": row.macd_signal,
                "macd_hist": row.macd_hist,
                "bb_upper": row.bb_upper,
                "bb_lower": row.bb_lower,
                "bb_mid": row.bb_mid,
                "atr_14": row.atr_14,
                "volume_sma_20": row.volume_sma_20,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
    )


def get_latest_indicators(symbol: str) -> dict[str, object] | None:
    normalized_symbol = symbol.strip().upper()

    session = SessionLocal()
    try:
        row = (
            session.query(StockIndicator)
            .filter(StockIndicator.symbol == normalized_symbol)
            .order_by(StockIndicator.trade_date.desc())
            .first()
        )
    finally:
        session.close()

    if row is None:
        return None

    return {
        "symbol": row.symbol,
        "trade_date": row.trade_date,
        "ema_20": row.ema_20,
        "ema_50": row.ema_50,
        "rsi_14": row.rsi_14,
        "macd_line": row.macd_line,
        "macd_signal": row.macd_signal,
        "macd_hist": row.macd_hist,
        "bb_upper": row.bb_upper,
        "bb_lower": row.bb_lower,
        "bb_mid": row.bb_mid,
        "atr_14": row.atr_14,
        "volume_sma_20": row.volume_sma_20,
        "updated_at": row.updated_at,
    }
