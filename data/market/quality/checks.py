from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from data.market.calendar import VN_AFTERNOON_START, VN_MORNING_END, VN_TIMEZONE, get_current_session, is_trading_day


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _to_vn_timestamp_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if getattr(parsed.dt, "tz", None) is None:
        return parsed.dt.tz_localize(VN_TIMEZONE)
    return parsed.dt.tz_convert(VN_TIMEZONE)


def _to_vn_timestamp(value: datetime | str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize(VN_TIMEZONE)
    return timestamp.tz_convert(VN_TIMEZONE)


def _normalize_expected_timestamps(expected_timestamps: list[datetime | str]) -> list[pd.Timestamp]:
    return [_to_vn_timestamp(value) for value in expected_timestamps]


def check_missing_bars(
    rows: pd.DataFrame | list[dict[str, object]],
    expected_timestamps: list[datetime | str],
) -> list[pd.Timestamp]:
    frame = _to_dataframe(rows)
    expected = _normalize_expected_timestamps(expected_timestamps)
    if not expected:
        return []
    if frame.empty or "ts" not in frame.columns:
        return expected

    actual = {
        value
        for value in _to_vn_timestamp_series(frame["ts"]).tolist()
        if not pd.isna(value)
    }
    return [timestamp for timestamp in expected if timestamp not in actual]


def check_duplicate_bars(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    frame = _to_dataframe(rows)
    if frame.empty or "symbol" not in frame.columns or "ts" not in frame.columns:
        return pd.DataFrame(columns=list(frame.columns))

    duplicates = frame.duplicated(subset=["symbol", "ts"], keep=False)
    return frame.loc[duplicates].copy().reset_index(drop=True)


def check_invalid_ohlc(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    frame = _to_dataframe(rows)
    required = ["open", "high", "low", "close"]
    if frame.empty or any(column not in frame.columns for column in required):
        return pd.DataFrame(columns=list(frame.columns))

    numeric = {
        column: pd.to_numeric(frame[column], errors="coerce")
        for column in required
    }
    mask = pd.Series(False, index=frame.index)
    for column, values in numeric.items():
        mask = mask | ((values < 0) & values.notna())

    comparable = numeric["open"].notna() & numeric["high"].notna() & numeric["low"].notna() & numeric["close"].notna()
    mask = mask | (
        comparable
        & (
            (numeric["high"] < numeric["open"])
            | (numeric["high"] < numeric["close"])
            | (numeric["high"] < numeric["low"])
            | (numeric["low"] > numeric["open"])
            | (numeric["low"] > numeric["close"])
            | (numeric["low"] > numeric["high"])
        )
    )

    if "volume" in frame.columns:
        volumes = pd.to_numeric(frame["volume"], errors="coerce")
        mask = mask | ((volumes < 0) & volumes.notna())

    return frame.loc[mask].copy().reset_index(drop=True)


def check_out_of_session(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    frame = _to_dataframe(rows)
    if frame.empty or "ts" not in frame.columns:
        return pd.DataFrame(columns=list(frame.columns))

    timestamps = _to_vn_timestamp_series(frame["ts"])
    mask = pd.Series(False, index=frame.index)
    for index, value in timestamps.items():
        if pd.isna(value):
            mask.loc[index] = True
            continue
        current_time = value.time()
        if VN_MORNING_END <= current_time < VN_AFTERNOON_START:
            mask.loc[index] = True
            continue
        if not is_trading_day(value) or get_current_session(value) is None:
            mask.loc[index] = True

    return frame.loc[mask].copy().reset_index(drop=True)


def check_stale_data(
    rows: pd.DataFrame | list[dict[str, object]],
    reference_time: datetime | str,
    stale_after: timedelta,
) -> pd.DataFrame:
    frame = _to_dataframe(rows)
    if frame.empty or "ts" not in frame.columns:
        return pd.DataFrame(columns=list(frame.columns))

    reference_ts = _to_vn_timestamp(reference_time)
    timestamps = _to_vn_timestamp_series(frame["ts"])
    mask = (reference_ts - timestamps) > stale_after
    mask = mask.fillna(False)
    return frame.loc[mask].copy().reset_index(drop=True)
