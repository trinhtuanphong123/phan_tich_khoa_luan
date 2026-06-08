from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from data.market.calendar import (
    VN_AFTERNOON_START,
    VN_MORNING_END,
    VN_TIMEZONE,
    get_current_session,
    is_trading_day,
)


@dataclass(frozen=True)
class ValidationResult:
    valid_rows: pd.DataFrame
    invalid_rows: pd.DataFrame
    quality_report: dict[str, Any]


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _to_vn_timestamp(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if getattr(parsed.dt, "tz", None) is None:
        return parsed.dt.tz_localize(VN_TIMEZONE)
    return parsed.dt.tz_convert(VN_TIMEZONE)


def _empty_result(columns: list[str]) -> ValidationResult:
    return ValidationResult(
        valid_rows=pd.DataFrame(columns=columns),
        invalid_rows=pd.DataFrame(columns=columns + ["validation_errors"]),
        quality_report={
            "total_rows": 0,
            "valid_row_count": 0,
            "invalid_row_count": 0,
            "error_counts": {},
        },
    )


def _ensure_columns(
    frame: pd.DataFrame,
    required_columns: list[str],
    errors: dict[int, list[str]],
) -> pd.DataFrame:
    for column in required_columns:
        if column in frame.columns:
            continue
        frame[column] = None
        for index in frame.index:
            _append_error(errors, index, f"missing_column_{column}")
    return frame


def _append_error(errors: dict[int, list[str]], index: int, error: str) -> None:
    errors.setdefault(index, []).append(error)


def _check_required_fields(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    for index, value in frame["symbol"].items():
        if pd.isna(value) or not str(value).strip():
            _append_error(errors, index, "symbol_missing")

    for index, value in frame["ts"].items():
        if pd.isna(value):
            _append_error(errors, index, "timestamp_missing")


def _check_price_rules(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    price_columns = ["open", "high", "low", "close"]
    for column in price_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        for index, value in values.items():
            if pd.notna(value) and value < 0:
                _append_error(errors, index, f"{column}_negative")

    numeric = {column: pd.to_numeric(frame[column], errors="coerce") for column in price_columns}
    for index in frame.index:
        open_value = numeric["open"].loc[index]
        high_value = numeric["high"].loc[index]
        low_value = numeric["low"].loc[index]
        close_value = numeric["close"].loc[index]

        comparable = [open_value, high_value, low_value, close_value]
        if any(pd.isna(value) for value in comparable):
            continue

        if high_value < max(open_value, close_value, low_value):
            _append_error(errors, index, "high_out_of_range")
        if low_value > min(open_value, close_value, high_value):
            _append_error(errors, index, "low_out_of_range")


def _check_volume_rules(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    volumes = pd.to_numeric(frame["volume"], errors="coerce")
    for index, value in volumes.items():
        if pd.notna(value) and value < 0:
            _append_error(errors, index, "volume_negative")


def _check_duplicates(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    duplicates = frame.duplicated(subset=["symbol", "ts"], keep=False)
    for index, is_duplicate in duplicates.items():
        if is_duplicate:
            _append_error(errors, index, "duplicate_symbol_timestamp")


def _is_lunch_break(value: datetime) -> bool:
    current_time = value.astimezone(VN_TIMEZONE).time()
    return VN_MORNING_END <= current_time < VN_AFTERNOON_START


def _check_intraday_session_rules(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    for index, value in frame["ts"].items():
        if pd.isna(value):
            continue
        if _is_lunch_break(value):
            _append_error(errors, index, "timestamp_in_lunch_break")
            continue
        if not is_trading_day(value):
            _append_error(errors, index, "timestamp_not_on_trading_day")
            continue
        if get_current_session(value) is None:
            _append_error(errors, index, "timestamp_outside_trading_session")


def _check_daily_session_rules(frame: pd.DataFrame, errors: dict[int, list[str]]) -> None:
    for index, value in frame["trade_date"].items():
        if pd.isna(value):
            continue
        if not is_trading_day(pd.Timestamp(value).date()):
            _append_error(errors, index, "trade_date_not_on_trading_day")


def _build_result(frame: pd.DataFrame, errors: dict[int, list[str]]) -> ValidationResult:
    annotated = frame.copy()
    annotated["validation_errors"] = annotated.index.map(lambda index: errors.get(index, []))

    invalid_mask = annotated["validation_errors"].map(bool)
    valid_rows = annotated.loc[~invalid_mask, frame.columns].reset_index(drop=True)
    invalid_rows = annotated.loc[invalid_mask].reset_index(drop=True)

    error_counts: dict[str, int] = {}
    for row_errors in invalid_rows["validation_errors"]:
        for error in row_errors:
            error_counts[error] = error_counts.get(error, 0) + 1

    return ValidationResult(
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        quality_report={
            "total_rows": int(len(frame)),
            "valid_row_count": int(len(valid_rows)),
            "invalid_row_count": int(len(invalid_rows)),
            "error_counts": error_counts,
        },
    )


def validate_intraday(rows: pd.DataFrame | list[dict[str, object]]) -> ValidationResult:
    frame = _to_dataframe(rows)
    if frame.empty:
        return _empty_result(list(frame.columns))

    errors: dict[int, list[str]] = {}
    frame = _ensure_columns(
        frame,
        ["symbol", "ts", "trade_date", "open", "high", "low", "close", "volume"],
        errors,
    )
    frame["symbol"] = frame["symbol"].astype("string").str.upper()
    frame["ts"] = _to_vn_timestamp(frame["ts"])

    _check_required_fields(frame, errors)
    _check_price_rules(frame, errors)
    _check_volume_rules(frame, errors)
    _check_duplicates(frame, errors)
    _check_intraday_session_rules(frame, errors)
    return _build_result(frame, errors)


def validate_daily(rows: pd.DataFrame | list[dict[str, object]]) -> ValidationResult:
    frame = _to_dataframe(rows)
    if frame.empty:
        return _empty_result(list(frame.columns))

    errors: dict[int, list[str]] = {}
    frame = _ensure_columns(
        frame,
        ["symbol", "ts", "trade_date", "open", "high", "low", "close", "volume"],
        errors,
    )
    frame["symbol"] = frame["symbol"].astype("string").str.upper()
    frame["ts"] = _to_vn_timestamp(frame["ts"])

    _check_required_fields(frame, errors)
    _check_price_rules(frame, errors)
    _check_volume_rules(frame, errors)
    _check_duplicates(frame, errors)
    _check_daily_session_rules(frame, errors)
    return _build_result(frame, errors)
