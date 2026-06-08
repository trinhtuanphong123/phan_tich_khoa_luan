from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from data.market.quality.checks import (
    check_duplicate_bars,
    check_invalid_ohlc,
    check_missing_bars,
    check_out_of_session,
    check_stale_data,
)


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _normalize_expected_map(
    expected_timestamps: dict[str, list[datetime | str]] | list[datetime | str] | None,
    symbols: list[str],
) -> dict[str, list[datetime | str]]:
    if expected_timestamps is None:
        return {symbol: [] for symbol in symbols}
    if isinstance(expected_timestamps, dict):
        return {symbol: expected_timestamps.get(symbol, []) for symbol in symbols}
    return {symbol: expected_timestamps for symbol in symbols}


def _build_status(missing_bars: int, invalid_rows: int, stale_rows: int) -> str:
    if missing_bars == 0 and invalid_rows == 0 and stale_rows == 0:
        return "ok"
    if invalid_rows > 0:
        return "invalid"
    if missing_bars > 0:
        return "missing"
    return "stale"


def build_quality_report(
    *,
    run_id: str,
    rows: pd.DataFrame | list[dict[str, object]],
    interval: str,
    expected_timestamps: dict[str, list[datetime | str]] | list[datetime | str] | None = None,
    reference_time: datetime | str | None = None,
    stale_after: timedelta | None = None,
) -> list[dict[str, Any]]:
    frame = _to_dataframe(rows)
    if frame.empty or "symbol" not in frame.columns:
        return []

    symbols = sorted({str(symbol).strip().upper() for symbol in frame["symbol"].dropna().tolist() if str(symbol).strip()})
    expected_map = _normalize_expected_map(expected_timestamps, symbols)

    duplicate_rows = check_duplicate_bars(frame)
    invalid_ohlc_rows = check_invalid_ohlc(frame)
    out_of_session_rows = check_out_of_session(frame) if interval != "1d" else pd.DataFrame(columns=frame.columns)
    stale_rows = (
        check_stale_data(frame, reference_time, stale_after)
        if reference_time is not None and stale_after is not None
        else pd.DataFrame(columns=frame.columns)
    )

    reports: list[dict[str, Any]] = []
    for symbol in symbols:
        symbol_rows = frame.loc[frame["symbol"].astype("string").str.upper() == symbol].copy()
        symbol_missing = check_missing_bars(symbol_rows, expected_map.get(symbol, []))

        symbol_invalid = pd.concat(
            [
                duplicate_rows.loc[duplicate_rows["symbol"].astype("string").str.upper() == symbol],
                invalid_ohlc_rows.loc[invalid_ohlc_rows["symbol"].astype("string").str.upper() == symbol],
                out_of_session_rows.loc[out_of_session_rows["symbol"].astype("string").str.upper() == symbol],
                stale_rows.loc[stale_rows["symbol"].astype("string").str.upper() == symbol],
            ],
            ignore_index=True,
        ).drop_duplicates()

        expected_bars = len(expected_map.get(symbol, []))
        actual_bars = int(len(symbol_rows))
        invalid_count = int(len(symbol_invalid))
        stale_count = int(
            len(stale_rows.loc[stale_rows["symbol"].astype("string").str.upper() == symbol])
        )

        reports.append(
            {
                "run_id": run_id,
                "symbol": symbol,
                "interval": interval,
                "expected_bars": expected_bars,
                "actual_bars": actual_bars,
                "missing_bars": len(symbol_missing),
                "invalid_rows": invalid_count,
                "status": _build_status(len(symbol_missing), invalid_count, stale_count),
            }
        )

    return reports


def summarize_ingestion_quality(reports: list[dict[str, Any]]) -> dict[str, Any]:
    if not reports:
        return {
            "run_id": None,
            "symbol_count": 0,
            "expected_bars": 0,
            "actual_bars": 0,
            "missing_bars": 0,
            "invalid_rows": 0,
            "status": "empty",
        }

    statuses = {str(report["status"]) for report in reports}
    if statuses == {"ok"}:
        status = "ok"
    elif "invalid" in statuses:
        status = "invalid"
    elif "missing" in statuses:
        status = "missing"
    else:
        status = "stale"

    return {
        "run_id": reports[0]["run_id"],
        "symbol_count": len(reports),
        "expected_bars": sum(int(report["expected_bars"]) for report in reports),
        "actual_bars": sum(int(report["actual_bars"]) for report in reports),
        "missing_bars": sum(int(report["missing_bars"]) for report in reports),
        "invalid_rows": sum(int(report["invalid_rows"]) for report in reports),
        "status": status,
    }
