from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from data.market.fetcher import fetch_daily_ohlcv
from data.market.normalizer import normalize_daily
from data.market.rate_limiter import RateLimiter
from data.market.store import store_daily_rows
from data.market.universe import get_priority_symbols
from data.storage.ingestion_repo import finish_run, record_error, start_run


def _load_root_dotenv() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")


def _fetch_symbol_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    rate_limiter: RateLimiter,
):
    last_error: Exception | None = None
    for _ in range(rate_limiter.max_retries):
        try:
            rate_limiter.wait()
            raw = fetch_daily_ohlcv(symbol, start_date=start_date, end_date=end_date)
            rate_limiter.register_success()
            return raw
        except Exception as exc:
            last_error = exc
            should_retry = rate_limiter.register_failure(exc, context=f"fetch_daily_ohlcv:{symbol}")
            if not should_retry:
                break
            rate_limiter.backoff()

    if last_error is None:
        raise RuntimeError(f"daily fetch failed for {symbol}")
    raise last_error


def main() -> None:
    _load_root_dotenv()

    today = datetime.now().date()
    start_date = (today - timedelta(days=7)).isoformat()
    end_date = today.isoformat()
    symbols = get_priority_symbols()
    rate_limiter = RateLimiter()

    run_id = start_run(
        job_type="market_daily_ingestion",
        interval="1d",
        window_start=start_date,
        window_end=end_date,
    )

    rows_written = 0
    symbols_ok = 0
    symbols_failed = 0

    print(
        f"[market_ingest_daily] run_id={run_id} interval=1d "
        f"window_start={start_date} window_end={end_date} symbols={len(symbols)}"
    )

    try:
        for symbol in symbols:
            try:
                raw_df = _fetch_symbol_daily(symbol, start_date, end_date, rate_limiter)
                normalized_df = normalize_daily(raw_df, symbol)
                store_result = store_daily_rows(normalized_df)
                quality_report = store_result["quality_report"]
                stored_count = int(quality_report.get("stored_row_count", 0))
                invalid_count = int(quality_report.get("invalid_row_count", 0))

                rows_written += stored_count
                symbols_ok += 1

                print(
                    f"[market_ingest_daily] symbol={symbol} status=ok "
                    f"rows_stored={stored_count} invalid_rows={invalid_count}"
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
                    f"[market_ingest_daily] symbol={symbol} status=error "
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
        print(
            f"[market_ingest_daily] run_id={run_id} status={final_status} "
            f"rows_written={rows_written} symbols_ok={symbols_ok} symbols_failed={symbols_failed}"
        )
    except Exception as exc:
        finish_run(
            run_id=run_id,
            status="failed",
            rows_written=rows_written,
            symbols_success=symbols_ok,
            symbols_failed=symbols_failed,
        )
        print(
            f"[market_ingest_daily] run_id={run_id} status=failed "
            f"rows_written={rows_written} symbols_ok={symbols_ok} symbols_failed={symbols_failed} "
            f"error_type={type(exc).__name__} error={exc}"
        )
        raise


if __name__ == "__main__":
    main()
