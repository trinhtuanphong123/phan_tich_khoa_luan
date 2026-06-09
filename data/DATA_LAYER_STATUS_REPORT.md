# Data Layer Status Report

This document records the current status of the non-news `data/` layer as of June 10, 2026. It focuses on the market, storage, and features paths that are currently active in code.

## Scope

Included:

- `data/market`
- `data/storage`
- `data/features`
- direct market-data consumers that sit on top of those modules

Excluded from detailed verification:

- `data/news`
- news ingestion and article processing paths

## 1. Executive Summary

The non-news data layer is no longer just a plan. It is implemented and usable for daily market ingestion and daily feature generation.

The main cleanup completed so far was a boundary standardization:

- public market/dataframe contract is now centered on:
  - `symbol`
  - `ts`
  - `trade_date`
- canonical market read/write logic is centered on:
  - [market_repo.py](/D:/TradingAgent-VN/data/storage/market_repo.py)
- the old mixed market access path through `DataRepository` has been reduced

The current system is good enough for:

- daily OHLCV ingestion
- daily market feature matrix creation
- daily indicator persistence
- downstream price-history reads from tools and services

The main unfinished areas are:

- non-market models still keep legacy `ticker` naming internally
- intraday orchestration now exists but still needs runtime validation with full dependencies installed
- `DataRepository` is now a compatibility facade, but some legacy callers still depend on it
- some performance limitations in row-by-row market upserts

## 2. Current Implemented Data Flow

The active non-news path in code is:

```text
External vnstock package / crawler sources
-> data.market.fetcher / vnstock.jobs.crawler
-> data.market.normalizer
-> data.market.validator
-> data.market.store
-> data.storage.market_repo
-> data.market.repository
-> data.features.market_features / indicators / build_features
-> data.storage.indicator_repo / feature_runs / local feature artifacts
```

There are two market ingestion entry styles currently present:

1. `data.market.ingest_daily`
   - the cleaner `data/`-native daily ingestion path

2. `vnstock.jobs.crawler`
   - a legacy-but-still-active operational path
   - now cleaned so market-specific persistence goes through `market_repo`

## 3. What Was Fixed

### 3.1 Naming consistency at the repo boundary

The biggest cleanup was standardizing outward-facing names.

Before cleanup, the active code mixed:

- `ticker` vs `symbol`
- `date` vs `ts`
- ORM attributes vs DB column names vs dataframe names

After cleanup, the active market/dataframe contract is:

- `symbol`
- `ts`
- `trade_date`

This standardization was applied mainly at the repository/API boundary instead of changing database columns directly.

### 3.2 Indicator repository cleanup

Updated file:

- [indicator_repo.py](/D:/TradingAgent-VN/data/storage/indicator_repo.py)

What changed:

- public outputs now use `symbol`
- public outputs return `trade_date`
- internal writes still use `StockIndicator.ticker`

Why this matters:

- feature-building code and market repositories now speak the same outward naming language

### 3.3 Feature and cluster naming cleanup

Updated files:

- [build_features.py](/D:/TradingAgent-VN/data/features/build_features.py)
- [cluster_repo.py](/D:/TradingAgent-VN/data/storage/cluster_repo.py)

What changed:

- feature-build loops and error metadata now use `symbol` in the active path
- cluster-history repo function now takes `symbol` rather than `ticker`

### 3.4 Market boundary cleanup in storage

Updated files:

- [market_repo.py](/D:/TradingAgent-VN/data/storage/market_repo.py)
- [repository.py](/D:/TradingAgent-VN/data/market/repository.py)

What changed:

- `market_repo` is now the canonical market storage/read layer
- `data.market.repository` is now a thin wrapper over `market_repo`
- duplicate market read implementations were removed from `data.market.repository`

Added in `market_repo`:

- `get_existing_trade_dates(...)`
- `delete_ohlcv_1d(...)`
- `_normalize_symbol(...)`

Why this matters:

- there is now one main place defining daily/intraday market read/write behavior

### 3.5 Removal of legacy daily market methods from DataRepository

Updated file:

- [base.py](/D:/TradingAgent-VN/data/storage/base.py)

What changed:

- removed active market helper methods from `DataRepository`:
  - `save_daily_data(...)`
  - `replace_daily_data(...)`
  - `get_price_history(...)`

What `DataRepository` is now used for:

- financial ratios
- symbol metadata
- sentiment
- agent logs

Why this matters:

- `DataRepository` no longer pretends to be the main market repository

### 3.6 Migration of consumers off DataRepository for market history

Updated files:

- [market_tool.py](/D:/TradingAgent-VN/vnstock/tools/market_tool.py)
- [quant_tool.py](/D:/TradingAgent-VN/vnstock/tools/quant_tool.py)
- [market_service.py](/D:/TradingAgent-VN/app/backend/services/market_service.py)
- [run.py](/D:/TradingAgent-VN/run.py)

What changed:

- market history reads now go through `market_repo.get_daily_ohlcv(...)`
- tools/services no longer depend on removed `DataRepository` market methods
- `market_tool` still uses `DataRepository` for sentiment only
- `quant_tool` still uses `DataRepository` for ratios and sentiment only

### 3.7 Crawler market-path cleanup

Updated file:

- [crawler.py](/D:/TradingAgent-VN/vnstock/jobs/crawler.py)

What changed:

- symbol history start lookup uses `market_repo.get_latest_bar_time(...)`
- benchmark history start lookup uses `market_repo.get_latest_bar_time(...)`
- replace-mode delete uses `market_repo.delete_ohlcv_1d(...)`
- incremental count uses `market_repo.get_existing_trade_dates(...)`
- daily writes use `market_repo.upsert_ohlcv_1d(...)`
- stale comment now reflects `market_repo` as the market persistence path

What stayed on `DataRepository`:

- financial ratio syncing
- symbol metadata syncing

That split is correct for the current design.

## 4. Current Code Design

## 4.1 Designed non-news data layer

The practical target design, based on the current code direction, is:

```text
Layer 1: Source adapters
- data.market.fetcher
- vnstock.jobs.crawler

Layer 2: Market normalization / validation
- data.market.normalizer
- data.market.validator
- data.market.quality

Layer 3: Canonical market persistence
- data.storage.market_repo

Layer 4: Read-side market API
- data.market.repository

Layer 5: Feature generation
- data.features.market_features
- data.features.indicators
- data.features.cluster_features
- data.features.build_features

Layer 6: Non-market support repos
- data.storage.indicator_repo
- data.storage.cluster_repo
- data.storage.ingestion_repo
- data.storage.base / repo (legacy support for metadata, ratios, sentiment)
```

### Contract by layer

For market dataframes and repo outputs, the intended contract is:

- `symbol`
- `ts`
- `trade_date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `value`
- daily only:
  - `buy_foreign`
  - `sell_foreign`

For ORM/database internals, legacy names may still exist:

- `ticker`
- `date`
- `timestamp`

Those should stay internal until a deliberate ORM refactor is approved.

## 4.2 Module-by-module explanation

### `data.market`

Key files:

- [fetcher.py](/D:/TradingAgent-VN/data/market/fetcher.py)
- [normalizer.py](/D:/TradingAgent-VN/data/market/normalizer.py)
- [validator.py](/D:/TradingAgent-VN/data/market/validator.py)
- [store.py](/D:/TradingAgent-VN/data/market/store.py)
- [repository.py](/D:/TradingAgent-VN/data/market/repository.py)
- [ingest_daily.py](/D:/TradingAgent-VN/data/market/ingest_daily.py)

Role:

- fetch raw market data
- normalize it into canonical rows
- validate row quality
- hand off persistence to `market_repo`
- expose a stable read-side interface to feature code

Important current state:

- daily ingestion exists and is runnable
- intraday read/write primitives exist
- intraday orchestration is not fully implemented

### `data.storage.market_repo`

Key file:

- [market_repo.py](/D:/TradingAgent-VN/data/storage/market_repo.py)

Role:

- canonical write path for:
  - `upsert_ohlcv_1d(...)`
  - `upsert_ohlcv_5m(...)`
- canonical read path for:
  - `get_ohlcv_1d(...)`
  - `get_ohlcv_5m(...)`
  - `get_daily_ohlcv(...)`
  - `get_latest_bar_time(...)`
  - `find_missing_bars(...)`
- market bookkeeping helpers:
  - `get_existing_trade_dates(...)`
  - `delete_ohlcv_1d(...)`

Why it is the center of the current design:

- it defines the actual public dataframe contract for market history
- downstream tools now depend on it directly

### `data.storage.base` / `data.storage.repo`

Key files:

- [base.py](/D:/TradingAgent-VN/data/storage/base.py)
- [repo.py](/D:/TradingAgent-VN/data/storage/repo.py)

Role now:

- generic repository helpers
- narrower domain repos:
  - `ratio_repo.py`
  - `symbol_repo.py`
  - `sentiment_repo.py`
  - `agent_log_repo.py`
- compatibility facade in `repo.py`

Important correction:

- this is no longer the active market-history API
- `DataRepository` remains only as a compatibility layer

### `data.storage.indicator_repo`

Key file:

- [indicator_repo.py](/D:/TradingAgent-VN/data/storage/indicator_repo.py)

Role:

- persist daily technical indicators
- read indicator history
- read latest indicators

Current outward contract:

- `symbol`
- `trade_date`
- indicator columns

### `data.features`

Key files:

- [market_features.py](/D:/TradingAgent-VN/data/features/market_features.py)
- [indicators.py](/D:/TradingAgent-VN/data/features/indicators.py)
- [cluster_features.py](/D:/TradingAgent-VN/data/features/cluster_features.py)
- [feature_store.py](/D:/TradingAgent-VN/data/features/feature_store.py)
- [build_features.py](/D:/TradingAgent-VN/data/features/build_features.py)

Role:

- transform stored OHLCV into model-ready daily features
- compute daily technical indicators
- persist feature-run metadata
- save matrix artifacts to local disk

Current output types:

1. feature matrices
   - multi-index dataframe structure
   - stored locally as artifact files

2. stock indicators
   - row-oriented daily indicator table in database

## 5. Current Behavior by Workflow

### Workflow A: Daily market ingestion

Main path:

```text
data.market.ingest_daily
-> fetch_daily_ohlcv
-> normalize_daily_ohlcv
-> validate_market_rows
-> store_daily_rows
-> market_repo.upsert_ohlcv_1d
```

Writes to:

- `market_ohlcv_1d`
- `ingestion_runs`
- `ingestion_errors`

### Workflow B: Daily feature generation

Main path:

```text
data.features.build_features
-> build_market_feature_matrix
-> save_market_features
-> get_daily_ohlcv per symbol
-> compute_indicators
-> save_stock_indicators
```

Writes to:

- local feature artifact files
- `feature_runs`
- `stock_indicators`

### Workflow C: Tool/service market reads

Main path:

```text
tool/service
-> market_repo.get_daily_ohlcv(...)
```

Examples:

- `vnstock.tools.market_tool`
- `vnstock.tools.quant_tool`
- `app.backend.services.market_service`
- `run.py`

## 6. Remaining Issues

## 6.1 ORM naming in `models.py`

Market-facing ORM attributes have now been standardized:

- `Ticker.symbol`
- `MarketOHLCV5m.symbol`
- `MarketOHLCV5m.ts`
- `MarketOHLCV1d.symbol`
- `MarketOHLCV1d.ts`
- `StockIndicator.symbol`

Compatibility aliases still exist for older callers:

- `ticker`
- `timestamp`
- `date`

The remaining issue is narrower:

- non-market models such as ratios, sentiment, and logs still use `ticker`
- compatibility aliases need to remain until legacy callers are migrated

## 6.2 Intraday orchestration needs runtime validation

What exists:

- intraday storage model
- intraday fetch primitives
- intraday repository reads/writes
- runnable intraday ingestion job:
  - [ingest_intraday.py](/D:/TradingAgent-VN/data/market/ingest_intraday.py)
- watermark-driven window resolution

What is still missing:

- runtime verification in an environment with `pandas` and full market dependencies
- reconciliation workflow
- deployment-side scheduling confirmation if run through ECS/EventBridge

## 6.3 Performance limitations in market upserts

Current behavior in `market_repo`:

- row-by-row ORM lookup
- row-by-row create/update

Why this matters:

- correct for now
- may become slow for larger backfills or denser intraday windows

Potential later fix:

- batched upserts or database-native upsert logic

## 6.4 Legacy callers still use `DataRepository`

Current state:

- narrower repos now exist for ratios, symbol metadata, sentiment, and agent logs
- `DataRepository` aggregates them for compatibility

Why this still matters:

- some legacy callers still import `DataRepository`
- those callers should migrate gradually to the narrower repos

## 6.5 Feature artifacts are local-disk only

Current behavior:

- [feature_store.py](/D:/TradingAgent-VN/data/features/feature_store.py) saves artifacts to local disk

What this means:

- good enough for local runs
- not yet a distributed artifact-storage design

## 6.6 News feature path is not implemented

Current state:

- [news_features.py](/D:/TradingAgent-VN/data/features/news_features.py) exists but is effectively empty

This is outside the current priority, but it remains an unfinished part of the broader data design.

## 7. Recommended Next Steps

Recommended order:

1. Freeze the current market boundary contract
   - no new market-facing code should expose `ticker` / `date`
   - use `symbol` / `ts` / `trade_date`

2. Add lightweight tests around the canonical repos
   - `market_repo`
   - `indicator_repo`
   - `build_features`
   - focus on column-contract verification

3. Migrate remaining legacy callers off `DataRepository`
   - crawler
   - news processor
   - any other compatibility-only users

4. Add runtime verification for intraday ingestion
   - confirm dependency-complete environment
   - confirm real watermark-driven fetch/store behavior

5. Decide whether non-market models should also move from `ticker` to `symbol`
   - only after broader compatibility coverage exists

## 8. Current Bottom Line

The non-news data layer is now materially cleaner than before.

The most important completed result is this:

- one canonical market storage path
- one stable outward naming contract
- fewer legacy entry points for price history

The code is currently positioned as a daily market-data and daily-feature pipeline with a first complete intraday ingestion path, but it still needs runtime validation and gradual cleanup of legacy non-market naming.
