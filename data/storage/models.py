from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, synonym
from sqlalchemy.pool import NullPool

from config import paths


def _resolve_db_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.strip():
        return database_url.strip()
    return f"sqlite:///{paths.vnstock_db_path}"


DB_URL = _resolve_db_url()
IS_SQLITE = DB_URL.startswith("sqlite:")

engine: Engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False, "timeout": 30} if IS_SQLITE else {},
    poolclass=NullPool if IS_SQLITE else None,
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


class Ticker(Base):
    __tablename__ = "tickers"

    symbol = Column("symbol", String(16), primary_key=True)
    exchange = Column(String(16))
    sector = Column(String(128))
    priority = Column(Integer, default=3, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    company_name = Column(String(255))
    industry = Column(String(100))
    icb_name2 = Column(String(100))
    icb_name3 = Column(String(100))
    icb_name4 = Column(String(100))
    charter_capital = Column(BigInteger)
    outstanding_shares = Column(BigInteger)

    ticker = synonym("symbol")


class MarketOHLCV5m(Base):
    __tablename__ = "market_ohlcv_5m"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column("symbol", String(16), ForeignKey("tickers.symbol"), nullable=False, index=True)
    ts = Column("ts", DateTime(timezone=True), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    value = Column(Float)
    source = Column(String(64), default="vnstock", nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "ts", "source", name="uq_market_ohlcv_5m_symbol_ts_source"),
    )

    ticker = synonym("symbol")
    timestamp = synonym("ts")
    price = synonym("close")


class MarketOHLCV1d(Base):
    __tablename__ = "market_ohlcv_1d"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column("symbol", String(16), ForeignKey("tickers.symbol"), nullable=False, index=True)
    ts = Column("ts", DateTime(timezone=True), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)
    value = Column(Float)
    source = Column(String(64), default="vnstock", nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    buy_foreign = Column(BigInteger, default=0, nullable=False)
    sell_foreign = Column(BigInteger, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", "source", name="uq_market_ohlcv_1d_symbol_trade_date_source"),
    )

    ticker = synonym("symbol")
    date = synonym("ts")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(64), nullable=False)
    interval = Column(String(16))
    window_start = Column(DateTime(timezone=True))
    window_end = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(32), default="running", nullable=False)
    rows_written = Column(Integer, default=0, nullable=False)
    symbols_success = Column(Integer, default=0, nullable=False)
    symbols_failed = Column(Integer, default=0, nullable=False)
    details_json = Column(JSON)


class IngestionError(Base):
    __tablename__ = "ingestion_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("ingestion_runs.id"), index=True)
    symbol = Column(String(16), index=True)
    interval = Column(String(16))
    error_type = Column(String(64))
    error_message = Column(Text, nullable=False)
    context_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class IngestionWatermark(Base):
    __tablename__ = "ingestion_watermarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    interval = Column(String(16), nullable=False, index=True)
    last_success_ts = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "interval", name="uq_ingestion_watermarks_symbol_interval"),
    )


class MarketDataQualityReport(Base):
    __tablename__ = "market_data_quality_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, index=True)
    symbol = Column(String(16), nullable=False, index=True)
    interval = Column(String(16), nullable=False)
    expected_bars = Column(Integer, default=0, nullable=False)
    actual_bars = Column(Integer, default=0, nullable=False)
    missing_bars = Column(Integer, default=0, nullable=False)
    invalid_rows = Column(Integer, default=0, nullable=False)
    status = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class FeatureRun(Base):
    __tablename__ = "feature_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True, index=True)
    feature_set = Column(String(128))
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(32), default="running", nullable=False)
    artifact_path = Column(String(512))
    metadata_json = Column(JSON)


class StockIndicator(Base):
    __tablename__ = "stock_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column("ticker", String(16), ForeignKey("tickers.symbol"), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)

    ema_20 = Column(Float)
    ema_50 = Column(Float)
    rsi_14 = Column(Float)
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    bb_upper = Column(Float)
    bb_lower = Column(Float)
    bb_mid = Column(Float)
    atr_14 = Column(Float)
    volume_sma_20 = Column(Float)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_stock_indicators_ticker_date"),
    )

    ticker = synonym("symbol")


class ClusterRun(Base):
    __tablename__ = "cluster_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=False, unique=True, index=True)
    feature_run_id = Column(Integer, ForeignKey("feature_runs.id"), index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String(32), default="running", nullable=False)
    algorithm = Column(String(64))
    metadata_json = Column(JSON)


class StockCluster(Base):
    __tablename__ = "stock_clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_run_id = Column(Integer, ForeignKey("cluster_runs.id"), nullable=False, index=True)
    symbol = Column(String(16), ForeignKey("tickers.symbol"), nullable=False, index=True)
    cluster_label = Column(String(64), nullable=False, index=True)
    score = Column(Float)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("cluster_run_id", "symbol", name="uq_stock_clusters_run_symbol"),
    )


class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column("ticker", String(10), index=True, nullable=False)
    quarter = Column(String(10), index=True, nullable=False)
    trailing_eps = Column(Float)
    book_value_per_share = Column(Float)
    pe = Column(Float)
    pb = Column(Float)
    beta = Column(Float)
    roe = Column(Float)
    roa = Column(Float)
    debt_equity = Column(Float)
    net_revenue = Column(Float)
    net_profit = Column(Float)
    revenue_yoy = Column(Float)
    net_profit_yoy = Column(Float)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "quarter", name="uq_financial_ratios_ticker_quarter"),
    )

    ticker = synonym("symbol")


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    symbol = Column("ticker", String(10), index=True)
    action = Column(String(50))
    confidence = Column(String(50))
    reason = Column(Text)
    full_report_path = Column(String(255))

    ticker = synonym("symbol")


class DailySentiment(Base):
    __tablename__ = "daily_sentiment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime(timezone=True), index=True, nullable=False)
    symbol = Column("ticker", String(10), index=True, nullable=False)
    daily_score = Column(Float)
    confidence = Column(Float)
    impact_summary = Column(Text)

    __table_args__ = (
        UniqueConstraint("date", "ticker", name="uq_daily_sentiment"),
    )

    ticker = synonym("symbol")


class BacktestMetric(Base):
    __tablename__ = "backtest_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_name = Column(String(50), nullable=False)
    symbol = Column("ticker", String(10), nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    account_value = Column(Float)
    return_pct = Column(Float)
    total_pnl = Column(Float)
    win_rate = Column(Float)
    sharpe = Column(Float)
    trades = Column(Integer)

    ticker = synonym("symbol")


# Compatibility aliases for existing code paths.
Symbol = Ticker
MarketDataDaily = MarketOHLCV1d
MarketDataIntraday = MarketOHLCV5m


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
