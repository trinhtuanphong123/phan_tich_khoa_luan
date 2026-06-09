from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from data.market.calendar import (
    VN_AFTERNOON_START,
    VN_MORNING_END,
    VN_TIMEZONE,
    clip_window_to_trading_sessions,
    get_closed_bar_time,
    is_trading_day,
    is_trading_time,
)
from data.market.fetcher import fetch_intraday_ohlcv
from data.market.normalizer import normalize_intraday
from data.market.store import store_intraday_rows
from data.market.universe import get_priority_symbols
from data.storage.ingestion_repo import (
    finish_run,
    get_watermark,
    record_error,
    start_run,
    update_watermark,
)


def _load_root_dotenv() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")


def _parse_interval(interval: str) -> timedelta:
    match = re.fullmatch(r"(\d+)([mh])", interval.strip().lower())
    if match is None:
        raise ValueError(f"unsupported interval: {interval}")

    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "m":
        return timedelta(minutes=amount)
    return timedelta(hours=amount)


def _resolve_symbol_window(
    symbol: str,
    *,
    interval: str,
    now: datetime,
    delay_minutes: int,
    bootstrap_lookback_minutes: int,
) -> tuple[datetime, datetime] | None:
    interval_delta = _parse_interval(interval)
    fetch_end = get_closed_bar_time(now - timedelta(minutes=delay_minutes), interval=interval)

    watermark = get_watermark(symbol, interval)
    if watermark is None:
        start = fetch_end - timedelta(minutes=bootstrap_lookback_minutes)
    else:
        start = pd.Timestamp(watermark).to_pydatetime() + interval_delta

    if start > fetch_end:
        return None

    clipped = clip_window_to_trading_sessions(start, fetch_end + interval_delta)
    if clipped is None:
        return None

    clipped_start, clipped_end = clipped
    clipped_fetch_end = clipped_end - interval_delta
    if clipped_start > clipped_fetch_end:
        return None

    return clipped_start, clipped_fetch_end


def _latest_valid_timestamp(store_result: dict[str, Any]) -> datetime | None:
    valid_rows = store_result.get("valid_rows")
    if valid_rows is None or valid_rows.empty or "ts" not in valid_rows.columns:
        return None
    return pd.Timestamp(valid_rows["ts"].max()).to_pydatetime()


def run_intraday_ingestion(
    *,
    now: datetime | None = None,
    symbols: list[str] | None = None,
    interval: str = "5m",
    delay_minutes: int = 10,
    bootstrap_lookback_minutes: int = 30,
) -> dict[str, Any]:
    resolved_now = now or datetime.now(VN_TIMEZONE)
    if resolved_now.tzinfo is None:
        resolved_now = resolved_now.replace(tzinfo=VN_TIMEZONE)

    if not is_trading_day(resolved_now):
        return {"status": "skipped", "reason": "not_trading_day", "symbols": 0}

    if not is_trading_time(resolved_now):
        return {"status": "skipped", "reason": "outside_trading_session", "symbols": 0}

    resolved_symbols = symbols or get_priority_symbols()
    window_end = get_closed_bar_time(resolved_now - timedelta(minutes=delay_minutes), interval=interval)
    run_id = start_run(
        job_type="market_intraday_ingestion",
        interval=interval,
        window_start=None,
        window_end=window_end,
    )

    rows_written = 0
    symbols_ok = 0
    symbols_failed = 0
    symbols_skipped = 0

    try:
        for symbol in resolved_symbols:
            symbol_window = _resolve_symbol_window(
                symbol,
                interval=interval,
                now=resolved_now,
                delay_minutes=delay_minutes,
                bootstrap_lookback_minutes=bootstrap_lookback_minutes,
            )
            if symbol_window is None:
                symbols_skipped += 1
                continue

            start_ts, end_ts = symbol_window
            try:
                raw_df = fetch_intraday_ohlcv(symbol, start_ts, end_ts, interval=interval)
                normalized_df = normalize_intraday(raw_df, symbol)
                store_result = store_intraday_rows(normalized_df)
                quality_report = store_result["quality_report"]
                stored_count = int(quality_report.get("stored_row_count", 0))

                latest_ts = _latest_valid_timestamp(store_result)
                if latest_ts is not None:
                    update_watermark(symbol, interval, latest_ts)

                rows_written += stored_count
                symbols_ok += 1
                print(
                    f"[market_ingest_intraday] symbol={symbol} interval={interval} "
                    f"window_start={start_ts.isoformat()} window_end={end_ts.isoformat()} "
                    f"rows_stored={stored_count}"
                )
            except Exception as exc:
                symbols_failed += 1
                record_error(
                    run_id=run_id,
                    symbol=symbol,
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                print(
                    f"[market_ingest_intraday] symbol={symbol} interval={interval} status=error "
                    f"error_type={type(exc).__name__} error={exc}"
                )

        final_status = "completed" if symbols_failed == 0 else "completed_with_errors"
        finish_run(
            run_id=run_id,
            status=final_status,
            rows_written=rows_written,
            symbols_success=symbols_ok,
            symbols_failed=symbols_failed,
        )
        return {
            "status": final_status,
            "run_id": run_id,
            "interval": interval,
            "rows_written": rows_written,
            "symbols": len(resolved_symbols),
            "symbols_success": symbols_ok,
            "symbols_failed": symbols_failed,
            "symbols_skipped": symbols_skipped,
            "window_end": window_end,
        }
    except Exception:
        finish_run(
            run_id=run_id,
            status="failed",
            rows_written=rows_written,
            symbols_success=symbols_ok,
            symbols_failed=symbols_failed + 1,
        )
        raise


def main() -> None:
    _load_root_dotenv()

    result = run_intraday_ingestion(
        interval=os.getenv("MARKET_INTRADAY_INTERVAL", "5m"),
        delay_minutes=int(os.getenv("MARKET_INTRADAY_DELAY_MINUTES", "10")),
        bootstrap_lookback_minutes=int(os.getenv("MARKET_INTRADAY_BOOTSTRAP_LOOKBACK_MINUTES", "30")),
    )
    print(
        "[market_ingest_intraday] "
        f"status={result['status']} "
        f"symbols={result.get('symbols', 0)} "
        f"symbols_success={result.get('symbols_success', 0)} "
        f"symbols_failed={result.get('symbols_failed', 0)} "
        f"symbols_skipped={result.get('symbols_skipped', 0)} "
        f"rows_written={result.get('rows_written', 0)}"
    )


if __name__ == "__main__":
    main()
