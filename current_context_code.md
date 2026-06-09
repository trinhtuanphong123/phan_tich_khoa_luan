# Current Code Context

This file is a verified code-state summary for the current repository, with focus on the `data/` layer and excluding the news pipeline except where it affects shared architecture.

## 1. Current project direction in code

The repository is still mixed:

- The intended target is a Vietnamese stock co-movement clustering system.
- The codebase still contains legacy trading-agent and analysis-oriented code outside `data/`.
- Inside `data/`, the non-news market/storage/features path is already materially implemented, not just planned.

The current non-news data flow that actually exists in code is:

```text
vnstock package
-> data.market.fetcher
-> data.market.normalizer
-> data.market.validator
-> data.market.store
-> data.storage.market_repo / models
-> data.market.repository
-> data.features.market_features / indicators / build_features
```

## 2. What is actually present under `data/`

The `data/` tree currently contains these major modules:

```text
data/
  market/
    calendar.py
    fetcher.py
    ingest_daily.py
    normalizer.py
    rate_limiter.py
    repository.py
    schemas.py
    store.py
    universe.py
    validator.py
    quality/

  features/
    build_features.py
    cluster_features.py
    feature_store.py
    indicators.py
    market_features.py
    news_features.py
    schemas.py

  storage/
    db.py
    models.py
    market_repo.py
    indicator_repo.py
    ingestion_repo.py
    cluster_repo.py
    news_repo.py
    object_store.py
    base.py
    repo.py
    db/
```

Important correction:

- `data.market.ingest_daily` exists and is runnable.
- `data.features.build_features` exists and is runnable.
- `data.features.cluster_features` also exists, even though earlier context treated it as only planned.
- `data.features.news_features.py` exists as an empty file.

## 3. Verified status of `data/market`

### Implemented and usable

`data/market/calendar.py`

- Defines Vietnam timezone and session boundaries.
- Implements `is_trading_day`, `get_current_session`, `is_trading_time`, `get_closed_bar_time`, `get_fetch_window`, and `clip_window_to_trading_sessions`.

`data/market/fetcher.py`

- Fetches daily and intraday OHLCV through the installed `vnstock` package.
- Runs vnstock calls in a subprocess with a filtered `sys.path`.
- Supports:
  - `fetch_daily_ohlcv(...)`
  - `fetch_intraday_ohlcv(...)`
  - `fetch_symbol_batch(...)`
- Uses env-based sources:
  - `VNSTOCK_DAILY_SOURCE`, default `KBS`
  - `VNSTOCK_INTRADAY_SOURCE`, default `VCI`

`data/market/normalizer.py`

- Normalizes raw vnstock frames into canonical market rows.
- Produces columns such as:
  - `symbol`
  - `ts`
  - `trade_date`
  - `open`, `high`, `low`, `close`
  - `volume`, `value`
  - `source`
  - `fetched_at`
- Daily normalization also fills `buy_foreign` and `sell_foreign`.

`data/market/validator.py`

- Validates required fields, price rules, non-negative volume, duplicates, and trading-session constraints.
- Distinguishes daily and intraday validation.
- Returns a structured `ValidationResult` with:
  - `valid_rows`
  - `invalid_rows`
  - `quality_report`

`data/market/store.py`

- Wires validator output into storage upserts.
- `store_daily_rows(...)` uses `market_repo.upsert_ohlcv_1d`.
- `store_intraday_rows(...)` uses `market_repo.upsert_ohlcv_5m`.

`data/market/repository.py`

- Provides read-side access for downstream features and ML-facing code.
- Delegates to `data.storage.market_repo` when available.
- Exposes:
  - `get_ohlcv_5m`
  - `get_daily_ohlcv`
  - `get_latest_bar_time`
  - `find_missing_bars`

`data/market/universe.py`

- Hardcodes VN30, VN50, and VN80-like symbol sets with metadata.
- Supports config overrides via env vars:
  - `MARKET_SYMBOLS`
  - `MARKET_UNIVERSE_SYMBOLS`
  - `CUSTOM_WATCHLIST`
  - `MARKET_PRIORITY_SYMBOLS`
  - `MARKET_PRIORITY_UNIVERSE`
- Implements sharding through `split_symbols_into_shards(...)`.

`data/market/rate_limiter.py`

- Exists and is used by daily ingestion.
- Retry and backoff are already wired into `ingest_daily.py`.

`data/market/quality/`

- `checks.py` and `reports.py` exist.
- Quality reporting infrastructure is present, but `ingest_daily.py` currently only prints per-symbol quality output and does not persist separate quality-report rows.

### Runnable entrypoint that exists today

`data/market/ingest_daily.py`

- Loads root `.env`.
- Builds a 7-day daily backfill window ending today.
- Gets symbols from `get_priority_symbols()`.
- Starts an ingestion run via `data.storage.ingestion_repo.start_run(...)`.
- Fetches daily OHLCV per symbol with retry and rate limiting.
- Normalizes and stores rows through `store_daily_rows(...)`.
- Records per-symbol failures into `ingestion_errors`.
- Finishes the run in `ingestion_runs`.

### Important limitation

The current runnable ingestion entrypoint is only daily ingestion.

What is not implemented yet at orchestration level:

- no runnable intraday ingestion module
- no near-real-time scheduler logic in code
- no session-aware intraday fetch loop using watermarks
- no EOD reconciliation job

So the codebase has intraday building blocks, but not an implemented intraday pipeline.

## 4. Verified status of `data/features`

### Implemented and usable

`data/features/market_features.py`

- Builds market feature matrices from stored daily OHLCV.
- Uses `data.market.repository.get_daily_ohlcv(...)`.
- Computes:
  - `close`
  - `log_return`
  - `rolling_return`
  - `rolling_volatility`
  - `volume_change`
  - `liquidity_proxy`
- Returns a DataFrame with MultiIndex columns: `(feature_name, symbol)`.

`data/features/cluster_features.py`

- Exists and is usable now.
- Extracts a single feature slice, default `log_return`, into a clustering input matrix.
- Also provides:
  - `build_latest_feature_snapshot(...)`
  - `build_correlation_similarity_matrix(...)`

`data/features/indicators.py`

- Exists and computes technical indicators from OHLCV data.
- Current implementation is manual pandas-based calculation.
- It computes:
  - `ema_20`
  - `ema_50`
  - `rsi_14`
  - `macd_line`
  - `macd_signal`
  - `macd_hist`
  - `bb_upper`
  - `bb_lower`
  - `bb_mid`
  - `atr_14`
  - `volume_sma_20`

Important correction:

- The current code does not use `pandas-ta`, even though `requirements/data.txt` includes it and earlier context described it as the intended implementation.

`data/features/feature_store.py`

- Persists feature artifacts locally under `data/feature_artifacts/`.
- Saves:
  - pickle matrix file
  - JSON metadata file
- Uses `config.paths.data_dir`.

Important correction:

- Feature artifacts currently go to local disk, not Supabase Storage or S3.

### Runnable entrypoint that exists today

`data/features/build_features.py`

- Loads `.env` from `PROJECT_ROOT`.
- Pulls priority symbols.
- Builds a feature run record in `feature_runs`.
- Builds the market feature matrix.
- Saves the matrix artifact locally through `save_market_features(...)`.
- Fetches daily OHLCV per ticker again and computes indicators ticker by ticker.
- Saves indicators via `data.storage.indicator_repo.save_stock_indicators(...)`.
- Marks the feature run as `success`, `partial_success`, or `failed`.

### Important limitations

- `build_features.py` is daily-feature oriented only.
- It depends on stored daily OHLCV already being available.
- `news_features.py` is empty and not part of the current working path.

## 5. Verified status of `data/storage`

### Main reality of the storage layer

There are two different database entry styles in the code:

`data/storage/models.py`

- Defines SQLAlchemy models and also creates its own engine/session factory.
- Falls back to local SQLite at `config.paths.vnstock_db_path` when `DATABASE_URL` is not set.

`data/storage/db.py`

- Defines a separate engine/session helper.
- Requires `DATABASE_URL`.
- Is not the primary path used by the current market/features repos.

Important correction:

- The main repos currently use `SessionLocal` from `data.storage.models`, not `data.storage.db`.
- That means the effective behavior today is dual-mode:
  - PostgreSQL if `DATABASE_URL` is set
  - local SQLite fallback if it is not

### ORM models that already exist in `data/storage/models.py`

Implemented non-news tables include:

- `tickers`
- `market_ohlcv_5m`
- `market_ohlcv_1d`
- `ingestion_runs`
- `ingestion_errors`
- `ingestion_watermarks`
- `market_data_quality_reports`
- `feature_runs`
- `stock_indicators`
- `cluster_runs`
- `stock_clusters`

There are also legacy or non-MVP tables still present:

- `financial_ratios`
- `agent_logs`
- `daily_sentiment`
- `backtest_metrics`

Important correction:

- `stock_indicators` is not a tall key-value indicator table.
- It is a wide table with fixed columns such as `ema_20`, `rsi_14`, `macd_line`, and so on.

### Repos that are implemented and usable

`data/storage/market_repo.py`

- Upserts daily and intraday market rows.
- Reads back daily and intraday OHLCV.
- Finds missing bars.
- Uses row-by-row ORM upsert logic.

`data/storage/indicator_repo.py`

- Saves indicator rows per ticker and trade date.
- Reads indicator history and latest indicator snapshot.

`data/storage/ingestion_repo.py`

- Tracks ingestion runs.
- Records ingestion errors.
- Reads and updates watermarks.

Important correction:

- Watermark APIs exist, but `data.market.ingest_daily` does not currently use them.

`data/storage/cluster_repo.py`

- Already exists.
- Can create cluster runs and persist stock clusters.
- This is implemented even though the main ML pipeline is not the current focus.

### Mixed or secondary pieces

- `data/storage/object_store.py` exists but is not part of the current verified market/features flow.
- `data/storage/base.py` and `data/storage/repo.py` also exist and look like older compatibility layers, not the primary path used by the current data pipeline.

## 6. Verified configuration and dependency state

### `config.py`

Root `config.py` already exists and is actively used by the current data code.

Relevant verified exports:

- `PROJECT_ROOT`
- `paths.data_dir`
- `paths.vnstock_db_path`
- `paths.news_db_path`

Important correction:

- The code does not need a separate `config/paths.py`; the root `config.py` already fills that role.

### `requirements/data.txt`

Verified characteristics:

- Includes pandas, numpy, sqlalchemy, psycopg2-binary, python-dotenv
- Includes `pandas-ta`
- Includes several news-crawling dependencies

Important correction:

- `pandas-ta` is currently declared but not used by `data.features.indicators.py`.

### `Dockerfile.data`

Verified characteristics:

- Installs from `requirements/data.txt`
- Copies only `config.py` and `data/`
- Does not copy `ml/`, `app/`, or `dashboard/`
- Has no default `CMD`

Important correction:

- The file matches a data-worker image approach, but it currently assumes the external `vnstock` package is installed from requirements rather than relying on the local `vnstock/` directory.

## 7. What is implemented now vs still planned

### Implemented now

- Daily market fetch from vnstock
- Daily normalization and validation
- Daily and intraday storage repos
- Ingestion run/error persistence
- Universe loading and sharding
- Market feature matrix generation
- Correlation-ready feature slicing
- Precomputed indicator persistence
- Local feature artifact persistence
- Cluster run and cluster label storage

### Only partially implemented or still planned

- Runnable intraday ingestion workflow
- Watermark-driven incremental market ingestion
- Quality-report persistence during ingestion
- Artifact persistence outside local disk
- Standardized single database access path
- A clean removal of legacy tables and helper layers

## 8. Practical current mental model for continuing coding

The most accurate current mental model for the non-news data layer is:

```text
The market/storage/features code is already real and usable.

The system can:
  fetch daily OHLCV
  validate and store it
  build daily features
  compute and persist technical indicators
  persist feature and ingestion run metadata

The system cannot yet be described as having a complete near-real-time market pipeline.

Intraday support exists as lower-level primitives, but the orchestration path is not built.

Storage is currently pragmatic rather than fully standardized:
  the main repos use models.py sessions
  PostgreSQL works when DATABASE_URL is provided
  SQLite fallback still exists for local use

Feature artifacts are still local-disk artifacts.
```

## 9. Next coding priorities implied by the current code

If continuing the non-news data work, the next realistic priorities are:

1. Decide whether the project should keep SQLite fallback in `data.storage.models` or move fully to `DATABASE_URL`.
2. Implement a real intraday ingestion entrypoint using:
   - `fetch_intraday_ohlcv`
   - trading-session window logic
   - watermarks
   - shard scheduling
3. Persist market quality reports during ingestion instead of only returning them in memory.
4. Decide whether indicator calculation should stay manual or actually switch to `pandas-ta`.
5. Decide whether feature artifacts should remain local or move to Supabase Storage / object storage.

This is the verified current code context for the `data/` layer, excluding detailed news verification.
