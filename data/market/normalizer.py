from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd


VN_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
NORMALIZED_COLUMNS = [
    "symbol",
    "ts",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "value",
    "source",
    "fetched_at",
]


def _to_dataframe(raw: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(raw, pd.DataFrame):
        return raw.copy()
    return pd.DataFrame(raw)


def _snake_case(name: object) -> str:
    value = str(name).strip()
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    return value.strip("_").lower()


def _rename_to_snake_case(frame: pd.DataFrame) -> pd.DataFrame:
    renamed = {_column: _snake_case(_column) for _column in frame.columns}
    return frame.rename(columns=renamed)


def _first_available_column(frame: pd.DataFrame, candidates: list[str]) -> pd.Series:
    for candidate in candidates:
        if candidate in frame.columns:
            return frame[candidate]
    return pd.Series([None] * len(frame), index=frame.index)


def _to_vn_timestamp(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if getattr(parsed.dt, "tz", None) is None:
        return parsed.dt.tz_localize(VN_TIMEZONE)
    return parsed.dt.tz_convert(VN_TIMEZONE)


def _fetched_at_series(index: pd.Index) -> pd.Series:
    fetched_at = datetime.now(VN_TIMEZONE)
    return pd.Series([fetched_at] * len(index), index=index)


def normalize_intraday(
    raw: pd.DataFrame | list[dict[str, object]],
    symbol: str,
    source: str = "vnstock",
) -> pd.DataFrame:
    frame = _rename_to_snake_case(_to_dataframe(raw))
    if frame.empty:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    ts = _to_vn_timestamp(
        _first_available_column(frame, ["ts", "timestamp", "datetime", "time", "match_time", "date"])
    )
    close = pd.to_numeric(_first_available_column(frame, ["close", "price", "match_price"]), errors="coerce")
    volume = pd.to_numeric(_first_available_column(frame, ["volume", "match_volume", "total_volume"]), errors="coerce")
    value = pd.to_numeric(_first_available_column(frame, ["value", "turnover", "total_value"]), errors="coerce")
    if value.isna().all():
        value = close * volume

    normalized = pd.DataFrame(index=frame.index)
    normalized["symbol"] = symbol.strip().upper()
    normalized["ts"] = ts
    normalized["trade_date"] = ts.dt.date
    normalized["open"] = pd.to_numeric(_first_available_column(frame, ["open"]), errors="coerce")
    normalized["high"] = pd.to_numeric(_first_available_column(frame, ["high"]), errors="coerce")
    normalized["low"] = pd.to_numeric(_first_available_column(frame, ["low"]), errors="coerce")
    normalized["close"] = close
    normalized["volume"] = volume
    normalized["value"] = value
    normalized["source"] = source
    normalized["fetched_at"] = _fetched_at_series(frame.index)
    return normalized[NORMALIZED_COLUMNS]


def normalize_daily(
    raw: pd.DataFrame | list[dict[str, object]],
    symbol: str,
    source: str = "vnstock",
) -> pd.DataFrame:
    frame = _rename_to_snake_case(_to_dataframe(raw))
    if frame.empty:
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    trade_date = pd.to_datetime(
        _first_available_column(frame, ["trade_date", "date", "trading_date"]),
        errors="coerce",
    )
    ts = trade_date.dt.tz_localize(VN_TIMEZONE)
    close = pd.to_numeric(_first_available_column(frame, ["close"]), errors="coerce")
    volume = pd.to_numeric(_first_available_column(frame, ["volume"]), errors="coerce")
    value = pd.to_numeric(_first_available_column(frame, ["value", "turnover"]), errors="coerce")
    if value.isna().all():
        value = close * volume

    normalized = pd.DataFrame(index=frame.index)
    normalized["symbol"] = symbol.strip().upper()
    normalized["ts"] = ts
    normalized["trade_date"] = trade_date.dt.date
    normalized["open"] = pd.to_numeric(_first_available_column(frame, ["open"]), errors="coerce")
    normalized["high"] = pd.to_numeric(_first_available_column(frame, ["high"]), errors="coerce")
    normalized["low"] = pd.to_numeric(_first_available_column(frame, ["low"]), errors="coerce")
    normalized["close"] = close
    normalized["volume"] = volume
    normalized["value"] = value
    normalized["source"] = source
    normalized["fetched_at"] = _fetched_at_series(frame.index)
    return normalized[NORMALIZED_COLUMNS]
