# `app/backend` Architecture

This note analyzes only the `app/backend` folder.

## 1. Backend framework and real application entry file(s)

### Framework

The backend is a **FastAPI** application.

Evidence:

- `app/backend/main.py` creates `FastAPI(...)`
- it registers `CORSMiddleware`
- it mounts routers under `/api`

### Real entry files

Within this folder, the real application entrypoints are:

- [app/backend/main.py]( /D:/TradingAgent-VN/app/backend/main.py )
- [app/backend/bootstrap.py]( /D:/TradingAgent-VN/app/backend/bootstrap.py ) as the required pre-import setup module

`main.py` is the ASGI app definition. `bootstrap.py` is not the app itself, but it must run first because it mutates environment variables, `sys.path`, and runtime behavior before any project imports happen.

## 2. Main routers, services, schemas, and helper modules

### Routers

- `routers/analysis.py`
- `routers/market.py`
- `routers/portfolio.py`
- `routers/history.py`

### Services

- `services/analysis_service.py`
- `services/market_service.py`
- `services/portfolio_service.py`
- `services/history_service.py`

### Schemas

There is no separate `schemas/` package. The request schemas are defined inline in the router modules:

- `analysis.py`
  - `AnalyzeBody`
- `market.py`
  - `SyncBody`
- `portfolio.py`
  - `Position`
  - `PortfolioBody`

### Helper / infrastructure modules

- `bootstrap.py`
- `main.py`
- `services/__init__.py`
- `routers/__init__.py`

The `__init__.py` files are empty markers here; the important infrastructure work is in `bootstrap.py`.

## 3. API domains actually present

### `/api/health`

Defined directly in `main.py`.

- Returns `{"status": "ok"}`
- Used as the simplest liveness check

### Analysis domain

Routes:

- `POST /api/analyze`
- `GET /api/analyze/{job_id}`

Behavior:

- starts a job-based multi-agent analysis
- returns a `job_id` immediately
- lets the frontend poll for progress and final output

This is the most complex API domain in the backend.

### Market domain

Routes:

- `GET /api/market/prices`
- `GET /api/market/news`
- `POST /api/market/sync`

Behavior:

- reads latest prices
- reads recent news
- triggers manual sync of prices and/or news

### Portfolio domain

Routes:

- `GET /api/portfolio`
- `POST /api/portfolio`
- `GET /api/portfolio/value`

Behavior:

- loads and saves the app-local portfolio JSON
- computes current portfolio value using latest prices

### History domain

Routes:

- `GET /api/history`
- `GET /api/history/{analysis_id}`

Behavior:

- lists previous analyses
- fetches a stored analysis snapshot by id

## 4. Request flow: route -> service -> storage or downstream module

### Analysis flow

`POST /api/analyze`

1. `routers/analysis.py` validates the request body with `AnalyzeBody`.
2. It uppercases ticker symbols and creates an `AnalysisRequest`.
3. It calls `services.analysis_service.create_job(...)`.
4. `create_job()` allocates an in-memory job, dedupes near-duplicate requests, and schedules `_run_job(job)` on the event loop.

Inside `_run_job(job)`:

1. The service loads or receives the portfolio via `portfolio_service.load_portfolio()`.
2. It syncs prices through `market_service.sync_prices_today_async()`.
3. It crawls news through `market_service.crawl_news_lite_async()`.
4. It resolves the latest cached financial quarter for each ticker.
5. It runs the core agents:
   - `MacroAgent`
   - `TechnicalAgent`
   - `QuantAgent`
   - `NewsAgent`
   - `FinancialAgent`
6. It runs workflow logic:
   - Traditional
   - Kelly
   - Markowitz
   - Cognitive
7. It synthesizes a CIO decision.
8. It builds a Markdown report.
9. It serializes a history snapshot and persists it through `history_service.save_analysis(...)`.

`GET /api/analyze/{job_id}`

- `routers/analysis.py` calls `services.analysis_service.get_job_snapshot(job_id)`
- the service returns the current in-memory snapshot for polling

### Market flow

`GET /api/market/prices`

1. `routers/market.py` parses comma-separated tickers.
2. It calls `market_service.get_latest_prices(items)`.
3. `market_service` reads cached prices first, then falls back to `vnstock.database.repo.DataRepository`.
4. That repository reads from `data/vnstock.db`.

`GET /api/market/news`

1. `routers/market.py` calls `market_service.get_recent_news(limit=...)`.
2. `market_service` reads `app/data/news_cache.db`.

`POST /api/market/sync`

1. `routers/market.py` validates `SyncBody`.
2. If tickers are present, it calls `market_service.sync_prices_today_async(...)`.
3. If `include_news` is true, it calls `market_service.crawl_news_lite_async(...)`.
4. The service writes into `data/vnstock.db` for prices and `app/data/news_cache.db` for news.

### Portfolio flow

`GET /api/portfolio`

- `portfolio_service.load_portfolio()` reads `app/data/portfolio.json`

`POST /api/portfolio`

- `portfolio_service.save_portfolio(...)` writes `app/data/portfolio.json`

`GET /api/portfolio/value`

1. `portfolio_service.compute_value()` loads the portfolio JSON.
2. It calls `market_service.get_latest_prices(...)`.
3. It calculates market value, P&L, and percentage returns.

### History flow

`GET /api/history`

- `history_service.list_analyses()` scans `app/data/history/*.json`

`GET /api/history/{analysis_id}`

- `history_service.get_analysis(analysis_id)` reads a single JSON snapshot from `app/data/history/`

## 5. Dependencies on `config.py`, `vnstock/`, `app/data/`, and external APIs or databases

### Dependency on `config.py`

The backend does not import `config.py` everywhere directly, but it depends on it through the runtime path setup and through the downstream `vnstock` code it invokes.

Important linkage:

- `bootstrap.py` sets environment variables **before** project imports
- that matters because `vnstock/` modules read `config.py` and env values at import time
- `main.py` imports `bootstrap` first specifically to make those side effects happen

### Dependency on `vnstock/`

The backend is a thin API shell over `vnstock` business logic.

Direct vnstock dependencies include:

- `vnstock.agents.macro_agent.MacroAgent`
- `vnstock.agents.news_agent.NewsAgent`
- `vnstock.agents.technical_agent.TechnicalAgent`
- `vnstock.agents.quant_agent.QuantAgent`
- `vnstock.agents.financial_agent.FinancialAgent`
- `vnstock.tools.backtest.engine.get_latest_financial_quarter`
- `vnstock.core.llm.call_llm`
- `vnstock.database.repo.DataRepository`
- `vnstock.jobs.crawler.MarketCrawler`

This backend does not reimplement trading logic; it orchestrates the vnstock layer.

### Dependency on `app/data/`

`bootstrap.py` creates and owns the app-local runtime folder:

- `app/data/`
- `app/data/history/`
- `app/data/price_cache/`

Files stored here:

- `app/data/portfolio.json`
- `app/data/news_cache.db`
- `app/data/news_cache_flag.json`
- `app/data/price_cache/today.json`
- `app/data/price_cache/sync_flag.json`
- `app/data/history/*.json`

This folder is the backend’s writeable runtime state.

### Dependency on external APIs or databases

External or external-adjacent dependencies used by this backend:

- `data/vnstock.db`
  - read by `DataRepository`
  - source of latest prices and historical data
- `app/data/news_cache.db`
  - populated via the `tracking_news` crawler pipeline
- LLM proxy at `http://127.0.0.1:8317/v1`
  - set in `bootstrap.py`
  - used by `vnstock.core.llm.call_llm`
- CafeF / news crawling pipeline
  - driven indirectly through `tracking_news`
- `cognitive_trading`
  - imported for cognitive workflow execution

## 6. Orchestration code vs business logic vs adapter code

### Orchestration code

This code coordinates request flow but does not own the core domain calculations:

- `main.py`
- `bootstrap.py`
- `services/analysis_service.py`

`analysis_service.py` is especially important: it is the runtime orchestrator for the entire analysis job pipeline.

### Business logic

This code owns the real domain behavior for the backend surface:

- `services/market_service.py`
- `services/portfolio_service.py`
- `services/history_service.py`

These modules implement the backend’s actual data handling policies:

- price caching
- news crawling
- portfolio normalization and valuation
- history persistence

### Adapter code

These modules mostly translate HTTP requests into service calls or bridge to downstream systems:

- `routers/analysis.py`
- `routers/market.py`
- `routers/portfolio.py`
- `routers/history.py`

Also adapter-like:

- `bootstrap.py`
  - sets env vars
  - patches import/runtime behavior
  - bridges the backend to the rest of the repo safely

## 7. Central files vs secondary files

### Central files

These are the files that matter most for understanding the backend:

1. `main.py`
2. `bootstrap.py`
3. `services/analysis_service.py`
4. `services/market_service.py`
5. `services/portfolio_service.py`
6. `services/history_service.py`

Why:

- `main.py` defines the app and mounts the routers
- `bootstrap.py` defines the runtime environment
- `analysis_service.py` drives the most important API flow
- `market_service.py` and `portfolio_service.py` connect the API to persistent state
- `history_service.py` is the persistence sink for completed analyses

### Secondary files

These are important, but mostly as thin wrappers:

- `routers/analysis.py`
- `routers/market.py`
- `routers/portfolio.py`
- `routers/history.py`
- `services/__init__.py`
- `routers/__init__.py`
- `__init__.py`

They are useful for route names and request schemas, but they do not contain the main logic.

## 8. Exact next-file reading order

If a human is continuing the backend code walk, read these next in order:

1. [app/backend/main.py]( /D:/TradingAgent-VN/app/backend/main.py )
2. [app/backend/bootstrap.py]( /D:/TradingAgent-VN/app/backend/bootstrap.py )
3. [app/backend/routers/analysis.py]( /D:/TradingAgent-VN/app/backend/routers/analysis.py )
4. [app/backend/services/analysis_service.py]( /D:/TradingAgent-VN/app/backend/services/analysis_service.py )
5. [app/backend/routers/market.py]( /D:/TradingAgent-VN/app/backend/routers/market.py )
6. [app/backend/services/market_service.py]( /D:/TradingAgent-VN/app/backend/services/market_service.py )
7. [app/backend/routers/portfolio.py]( /D:/TradingAgent-VN/app/backend/routers/portfolio.py )
8. [app/backend/services/portfolio_service.py]( /D:/TradingAgent-VN/app/backend/services/portfolio_service.py )
9. [app/backend/routers/history.py]( /D:/TradingAgent-VN/app/backend/routers/history.py )
10. [app/backend/services/history_service.py]( /D:/TradingAgent-VN/app/backend/services/history_service.py )

If you want the highest-leverage path first, start with:

1. `main.py`
2. `bootstrap.py`
3. `services/analysis_service.py`
4. `services/market_service.py`
5. `services/portfolio_service.py`
