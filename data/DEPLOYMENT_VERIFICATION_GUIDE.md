# Deployment Verification Guide

This guide is for verifying the current market-data deployment path after the recent data-layer refactor.

It covers:

- daily ingestion verification
- intraday ingestion verification
- feature build verification
- database checks
- known remaining issues that are still outside the fully completed Market-data MVP

This guide is aligned to the current codebase as of June 10, 2026.

## 1. Scope

This guide verifies the **market-data MVP path**:

- `data.market.ingest_daily`
- `data.market.ingest_intraday`
- `data.features.build_features`
- `data.storage.market_repo`
- `data.storage.indicator_repo`

This guide does **not** treat the news pipeline as deployment-complete.

## 2. What Should Be Working Before You Start

The following should already exist in the repo:

- [data/market/ingest_daily.py](/D:/TradingAgent-VN/data/market/ingest_daily.py)
- [data/market/ingest_intraday.py](/D:/TradingAgent-VN/data/market/ingest_intraday.py)
- [data/features/build_features.py](/D:/TradingAgent-VN/data/features/build_features.py)
- [data/storage/models.py](/D:/TradingAgent-VN/data/storage/models.py)
- [data/storage/market_repo.py](/D:/TradingAgent-VN/data/storage/market_repo.py)
- [data/storage/indicator_repo.py](/D:/TradingAgent-VN/data/storage/indicator_repo.py)

## 3. Required Environment

You need:

1. Python environment with project dependencies installed
   - especially:
     - `pandas`
     - `sqlalchemy`
     - `python-dotenv`
     - `requests`
     - `vnstock`
     - `pandas_ta` if any downstream tool still imports it

2. A valid `.env`

3. A working `DATABASE_URL`, or working SQLite fallback path if that is still your local mode

4. Market source environment variables if required:
   - `VNSTOCK_DAILY_SOURCE`
   - `VNSTOCK_INTRADAY_SOURCE`
   - `VNSTOCK_API_KEY` if the source requires it

## 4. Recommended Verification Order

Run verification in this order:

1. database init
2. seed ticker master data
3. daily ingestion
4. intraday ingestion
5. feature build
6. database inspection
7. scheduler/deployment validation

Do not start from feature build first. It depends on stored market data already existing.

## 5. Step 1 — Initialize Database

Run:

```powershell
@'
from data.storage.models import init_db
init_db()
print("db_init_ok")
'@ | python -
```

Expected result:

- no exception
- tables created if missing

Core tables that should exist:

- `tickers`
- `market_ohlcv_1d`
- `market_ohlcv_5m`
- `stock_indicators`
- `ingestion_runs`
- `ingestion_errors`
- `ingestion_watermarks`
- `feature_runs`

## 6. Step 2 — Seed Ticker Master Data

Market tables depend on `tickers.symbol` foreign keys.

You must have ticker master rows before market upserts.

If you already have a seeding script, run it.

If not, use a small verification seed first:

```powershell
@'
from data.storage.models import SessionLocal, Ticker

symbols = ["FPT", "HPG", "MBB", "SSI", "VCB"]
session = SessionLocal()
try:
    for symbol in symbols:
        row = session.query(Ticker).filter(Ticker.symbol == symbol).first()
        if row is None:
            session.add(Ticker(symbol=symbol, exchange="HOSE", priority=1, is_active=True))
    session.commit()
    print("ticker_seed_ok")
finally:
    session.close()
'@ | python -
```

Expected result:

- no foreign-key errors later during ingestion

## 7. Step 3 — Verify Daily Ingestion

Run:

```powershell
python -m data.market.ingest_daily
```

Expected log shape:

- one run header
- per-symbol `status=ok` or `status=error`
- final summary with:
  - `rows_written`
  - `symbols_ok`
  - `symbols_failed`

Success criteria:

- process finishes without crashing
- at least some symbols store rows
- `ingestion_runs` gets a new `1d` run

Failure patterns to watch:

- source API returns empty frames for all symbols
- ticker master not seeded
- `DATABASE_URL` invalid
- environment missing source auth

## 8. Step 4 — Verify Intraday Ingestion

Run:

```powershell
python -m data.market.ingest_intraday
```

Important:

- this only does useful work during a Vietnamese trading session
- outside trading hours it may correctly return:
  - `status=skipped`

Suggested verification time:

- weekday
- morning or afternoon trading session in ICT

Useful environment overrides:

```powershell
$env:MARKET_INTRADAY_INTERVAL="5m"
$env:MARKET_INTRADAY_DELAY_MINUTES="10"
$env:MARKET_INTRADAY_BOOTSTRAP_LOOKBACK_MINUTES="30"
python -m data.market.ingest_intraday
```

Expected behavior:

- session check passes during trading time
- per-symbol intraday fetch window resolves from watermark
- valid rows are stored into `market_ohlcv_5m`
- watermark gets updated in `ingestion_watermarks`

Success criteria:

- process finishes without crashing
- `market_ohlcv_5m` receives rows
- `ingestion_watermarks` updates for processed symbols

Failure patterns to watch:

- no `pandas` in runtime
- intraday source returns no rows
- interval not supported
- timezone/session mismatch

## 9. Step 5 — Verify Feature Build

Run:

```powershell
python -m data.features.build_features
```

Expected behavior:

- feature run record created
- market feature matrix built
- artifact saved locally
- indicator rows written into `stock_indicators`

Success criteria:

- `feature_runs` gets a new row
- artifact path is written
- `stock_indicators` has fresh rows

Failure patterns to watch:

- no daily OHLCV exists yet
- per-symbol indicator calculation fails
- artifact directory permissions/path issue

## 10. Step 6 — Verify Database State

Run this inspection snippet:

```powershell
@'
from data.storage.models import SessionLocal, Ticker, MarketOHLCV1d, MarketOHLCV5m, StockIndicator, IngestionRun, IngestionWatermark, FeatureRun

session = SessionLocal()
try:
    print("tickers", session.query(Ticker).count())
    print("market_ohlcv_1d", session.query(MarketOHLCV1d).count())
    print("market_ohlcv_5m", session.query(MarketOHLCV5m).count())
    print("stock_indicators", session.query(StockIndicator).count())
    print("ingestion_runs", session.query(IngestionRun).count())
    print("ingestion_watermarks", session.query(IngestionWatermark).count())
    print("feature_runs", session.query(FeatureRun).count())
finally:
    session.close()
'@ | python -
```

Then inspect the latest rows:

```powershell
@'
from data.storage.models import SessionLocal, MarketOHLCV1d, MarketOHLCV5m, StockIndicator

session = SessionLocal()
try:
    print("latest_daily", session.query(MarketOHLCV1d).order_by(MarketOHLCV1d.ts.desc()).first())
    print("latest_intraday", session.query(MarketOHLCV5m).order_by(MarketOHLCV5m.ts.desc()).first())
    print("latest_indicator", session.query(StockIndicator).order_by(StockIndicator.trade_date.desc()).first())
finally:
    session.close()
'@ | python -
```

What to confirm:

- daily timestamps look correct
- intraday timestamps look correct
- symbols are uppercase
- indicators have recent `trade_date`

## 11. Step 7 — Verify Scheduling / Deployment

If deploying locally first:

1. run daily ingestion manually
2. run intraday ingestion manually during market session
3. run feature build manually

If deploying to ECS/EventBridge:

1. create task definitions for:
   - daily ingestion
   - intraday ingestion
   - feature build
2. run each task manually once
3. inspect logs
4. confirm database writes
5. only then enable schedules

Suggested schedule shape:

- daily ingestion after market close
- intraday ingestion during weekday sessions, conservative frequency
- feature build after daily ingestion

## 12. Fast Failure Checklist

If verification fails, check these first:

1. `.env` loaded correctly
2. `DATABASE_URL` valid
3. ticker master seeded
4. dependencies installed in the runtime actually executing the code
5. source API credentials/config valid
6. intraday run executed during Vietnamese trading hours

## 13. Parts Still Needing Fixes

This section is the exact answer to the two points you asked to surface.

### 13.1 Legacy naming still scattered outside the core market ORM contract

Status:

- core market ORM/storage contract is already standardized around:
  - `symbol`
  - `ts`
  - `trade_date`
- supporting storage models now also have canonical `symbol` ORM attributes with `ticker` aliases

What still needs cleanup later:

1. business-level function arguments and payloads still use `ticker`
   - this is common in:
     - CLI arguments
     - tool/report outputs
     - news-side code
     - RAG-side code

2. some SQL in non-market paths still uses `ticker` as the persisted column name
   - especially where the underlying DB schema is older or separate

3. documentation still mentions older naming in places
   - especially older deployment/status documents

What does **not** need to be treated as a blocker for market-data deployment:

- every user-facing string saying “ticker”
- every report payload key named `ticker`

What should be treated as a blocker:

- any remaining mismatch in the active market ingestion / feature pipeline between:
  - ORM attributes
  - dataframe contract
  - repository reads/writes

### 13.2 News support subsystems are still not complete for the Market-data MVP

Current known issues:

1. import-path problems remain in `data/news/`
   - old references like:
     - `data.tracking_news.app.*`
   - these break news deployment

2. `data/features/news_features.py` is not part of the official active execution flow
   - it is not the current market-data MVP path

3. news storage/deployment is separate from the core market-data path
   - SQLite/EFS concerns still apply

What needs fixing before any real news deployment:

1. fix all `data/news/` import paths
2. verify news ingest entrypoints run without `ModuleNotFoundError`
3. decide whether news remains on SQLite+EFS or moves into PostgreSQL
4. only then decide whether `news_features.py` becomes part of the official feature pipeline

What does **not** block market-data MVP deployment:

- the incomplete news pipeline
- `news_features.py` being outside the current official execution path

## 14. Practical Definition of “Deployment-Ready” for the Current MVP

You can treat the current market-data MVP as deployment-ready enough to trial if all of these are true:

1. daily ingestion runs and writes rows
2. intraday ingestion runs during market session and updates watermarks
3. feature build runs and writes indicators
4. ticker seeding is stable
5. no schema/runtime mismatch appears in logs

If those five checks pass, the current market-data path is ready for data collection.

