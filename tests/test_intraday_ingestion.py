from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

try:
    import pandas as pd
    from data.market.calendar import VN_TIMEZONE
    from data.market.ingest_intraday import _resolve_symbol_window, run_intraday_ingestion

    HAVE_INTRADAY_DEPS = True
except ImportError:
    pd = None
    VN_TIMEZONE = None
    _resolve_symbol_window = None
    run_intraday_ingestion = None
    HAVE_INTRADAY_DEPS = False


@unittest.skipUnless(HAVE_INTRADAY_DEPS, "intraday ingestion tests require pandas")
class IntradayIngestionTests(unittest.TestCase):
    def test_resolve_symbol_window_uses_watermark_and_next_bar(self) -> None:
        now = datetime(2026, 6, 10, 10, 17, tzinfo=VN_TIMEZONE)
        with patch("data.market.ingest_intraday.get_watermark", return_value=datetime(2026, 6, 10, 9, 55, tzinfo=VN_TIMEZONE)):
            window = _resolve_symbol_window(
                "FPT",
                interval="5m",
                now=now,
                delay_minutes=10,
                bootstrap_lookback_minutes=30,
            )

        self.assertIsNotNone(window)
        start_ts, end_ts = window
        self.assertEqual(start_ts, datetime(2026, 6, 10, 10, 0, tzinfo=VN_TIMEZONE))
        self.assertEqual(end_ts, datetime(2026, 6, 10, 10, 5, tzinfo=VN_TIMEZONE))

    def test_run_intraday_ingestion_skips_outside_session(self) -> None:
        now = datetime(2026, 6, 10, 8, 30, tzinfo=VN_TIMEZONE)
        result = run_intraday_ingestion(now=now, symbols=["FPT"])
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "outside_trading_session")

    def test_run_intraday_ingestion_updates_watermark_after_successful_store(self) -> None:
        now = datetime(2026, 6, 10, 10, 17, tzinfo=VN_TIMEZONE)
        valid_rows = pd.DataFrame(
            {
                "ts": [
                    pd.Timestamp(datetime(2026, 6, 10, 10, 0, tzinfo=VN_TIMEZONE)),
                    pd.Timestamp(datetime(2026, 6, 10, 10, 5, tzinfo=VN_TIMEZONE)),
                ]
            }
        )

        with (
            patch("data.market.ingest_intraday.start_run", return_value=77) as start_run,
            patch("data.market.ingest_intraday.finish_run") as finish_run,
            patch("data.market.ingest_intraday.record_error") as record_error,
            patch("data.market.ingest_intraday.get_watermark", return_value=datetime(2026, 6, 10, 9, 55, tzinfo=VN_TIMEZONE)),
            patch("data.market.ingest_intraday.fetch_intraday_ohlcv", return_value=pd.DataFrame({"dummy": [1]})) as fetch_intraday,
            patch("data.market.ingest_intraday.normalize_intraday", return_value=pd.DataFrame({"dummy": [1]})) as normalize_intraday,
            patch(
                "data.market.ingest_intraday.store_intraday_rows",
                return_value={
                    "quality_report": {"stored_row_count": 2},
                    "valid_rows": valid_rows,
                    "invalid_rows": pd.DataFrame(),
                },
            ) as store_intraday_rows,
            patch("data.market.ingest_intraday.update_watermark") as update_watermark,
        ):
            result = run_intraday_ingestion(
                now=now,
                symbols=["FPT"],
                interval="5m",
                delay_minutes=10,
                bootstrap_lookback_minutes=30,
            )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["rows_written"], 2)
        start_run.assert_called_once()
        record_error.assert_not_called()
        fetch_intraday.assert_called_once()
        normalize_intraday.assert_called_once()
        store_intraday_rows.assert_called_once()
        update_watermark.assert_called_once_with(
            "FPT",
            "5m",
            datetime(2026, 6, 10, 10, 5, tzinfo=VN_TIMEZONE),
        )
        finish_run.assert_called_once_with(
            run_id=77,
            status="completed",
            rows_written=2,
            symbols_success=1,
            symbols_failed=0,
        )


if __name__ == "__main__":
    unittest.main()
