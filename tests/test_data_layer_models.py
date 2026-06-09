from __future__ import annotations

import unittest
from datetime import date, datetime

from data.storage.models import (
    AgentLog,
    BacktestMetric,
    DailySentiment,
    FinancialRatio,
    MarketOHLCV1d,
    MarketOHLCV5m,
    StockIndicator,
    Ticker,
)


class ModelNamingContractTests(unittest.TestCase):
    def test_master_symbol_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = Ticker(symbol="FPT")
        self.assertEqual(row.symbol, "FPT")
        self.assertEqual(row.ticker, "FPT")

        row.ticker = "HPG"
        self.assertEqual(row.symbol, "HPG")

    def test_daily_market_model_keeps_ts_and_date_alias(self) -> None:
        ts = datetime(2026, 6, 10, 15, 0, 0)
        row = MarketOHLCV1d(symbol="FPT", ts=ts, trade_date=date(2026, 6, 10))
        self.assertEqual(row.symbol, "FPT")
        self.assertEqual(row.ticker, "FPT")
        self.assertEqual(row.ts, ts)
        self.assertEqual(row.date, ts)

        updated_ts = datetime(2026, 6, 11, 15, 0, 0)
        row.date = updated_ts
        self.assertEqual(row.ts, updated_ts)

    def test_intraday_market_model_keeps_ts_and_timestamp_alias(self) -> None:
        ts = datetime(2026, 6, 10, 10, 5, 0)
        row = MarketOHLCV5m(symbol="FPT", ts=ts, trade_date=date(2026, 6, 10))
        self.assertEqual(row.symbol, "FPT")
        self.assertEqual(row.ticker, "FPT")
        self.assertEqual(row.ts, ts)
        self.assertEqual(row.timestamp, ts)

        row.ticker = "MBB"
        self.assertEqual(row.symbol, "MBB")

    def test_indicator_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = StockIndicator(symbol="SSI", trade_date=date(2026, 6, 10))
        self.assertEqual(row.symbol, "SSI")
        self.assertEqual(row.ticker, "SSI")

        row.ticker = "VCB"
        self.assertEqual(row.symbol, "VCB")

    def test_financial_ratio_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = FinancialRatio(symbol="SSI", quarter="2026-Q2")
        self.assertEqual(row.symbol, "SSI")
        self.assertEqual(row.ticker, "SSI")

        row.ticker = "VCB"
        self.assertEqual(row.symbol, "VCB")

    def test_daily_sentiment_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = DailySentiment(symbol="SSI", date=datetime(2026, 6, 10))
        self.assertEqual(row.symbol, "SSI")
        self.assertEqual(row.ticker, "SSI")

        row.ticker = "VCB"
        self.assertEqual(row.symbol, "VCB")

    def test_agent_log_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = AgentLog(symbol="SSI")
        self.assertEqual(row.symbol, "SSI")
        self.assertEqual(row.ticker, "SSI")

        row.ticker = "VCB"
        self.assertEqual(row.symbol, "VCB")

    def test_backtest_metric_model_keeps_symbol_and_ticker_alias(self) -> None:
        row = BacktestMetric(symbol="SSI")
        self.assertEqual(row.symbol, "SSI")
        self.assertEqual(row.ticker, "SSI")

        row.ticker = "VCB"
        self.assertEqual(row.symbol, "VCB")


if __name__ == "__main__":
    unittest.main()
