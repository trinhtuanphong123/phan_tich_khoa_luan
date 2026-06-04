# Runtime Surface and Entry Points

This note is based only on:

- `run.py`
- `config.py`
- `requirements.txt`
- `app/backend/requirements.txt`
- `app/frontend/package.json`
- `dashboard/package.json`

The files `environment.yml` and `.env.example` were requested, but they are not present at the repository root in this workspace, so I do not use them as evidence here.

## 1. How the repository is started and in which modes

### Root CLI

The main runtime entrypoint is `python run.py`. It dispatches to subcommands and is the broadest operational surface in the repo.

Supported CLI modes from `run.py`:

- `crawl-vnstock`
- `crawl-news`
- `sync` and alias `prepare`
- `analyze`
- `backtest`
- `backtest-cognitive`
- `rag index`
- `rag query`
- `rag dashboard`

The CLI is asynchronous at the top level, but individual subcommands may call synchronous helpers or external processes.

### Realtime frontend

The frontend package is started from `app/frontend/package.json`:

- `npm run dev` -> `next dev -p 3001`
- `npm run build` -> `next build`
- `npm run start` -> `next start -p 3001`

This is the realtime UI surface for the app.

### Research dashboard

The dashboard package is started from `dashboard/package.json`:

- `npm run dev` -> `next dev -H 0.0.0.0 -p 8000`
- `npm run build` -> `next build`
- `npm run start` -> `next start -H 0.0.0.0 -p 8000`

This is the research/backtest presentation surface.

### Backend API

The inspected files show a backend dependency set and runtime config, but no explicit backend launch script.

What is clear from the files:

- `config.py` defines backend host/port-related settings via environment-driven config
- `app/backend/requirements.txt` declares FastAPI/Uvicorn/HTTP client dependencies

So the backend API is a real runtime subsystem, but its exact startup command is not defined in the files I was asked to inspect.

## 2. Which commands trigger which subsystem

### Market data ingestion

- `python run.py crawl-vnstock`
- `python run.py crawl-vnstock --tickers FPT,VCB,HPG`
- `python run.py crawl-vnstock --replace-existing`

Triggers:

- `vnstock.database.models.init_db()`
- `vnstock.jobs.crawler.MarketCrawler.sync_tickers()`
- writes to `data/vnstock.db` through `paths.vnstock_db_path`

### News ingestion

- `python run.py crawl-news --news-days 10 --source cafef`

Triggers:

- `tracking_news.app.ingest.run_once.main()`
- sets ingestion-window environment variables such as `INGEST_DATE_FROM`, `INGEST_DATE_TO`, `ENABLED_SOURCES`
- writes to the news database path from config

### One-shot sync

- `python run.py sync --tickers FPT,VCB --year 2025 --quarter Q4 --news-days 3`
- alias: `python run.py prepare ...`

Triggers:

- market sync into `data/vnstock.db`
- incremental news crawl
- financial report generation/caching through `vnstock.agents.financial_analysis.generate_financial_report()`

This is the closest thing in the CLI to an all-in-one preparation pipeline.

### Financial report generation

- `python run.py analyze --ticker FPT --year 2025 --quarter Q4`

Triggers:

- `vnstock.agents.financial_analysis.generate_financial_report()`
- report output under `vnstock/analysis_reports/`

### RAG ingestion

- `python run.py rag index --input vnstock/libs/data/financial_reports`

Triggers:

- `vnstock.libs.rag_engine.ingest.run_ingest()`
- builds or updates the RAG store under `vnstock/rag_storage/`

### RAG query

- `python run.py rag query --query "..."`

Triggers:

- `vnstock.libs.rag_engine.retrieval.query_func()`
- returns contexts plus answer text

### RAG dashboard

- `python run.py rag dashboard --port 8501`

Triggers:

- launches Streamlit via `streamlit run`
- points at `vnstock/libs/rag_engine/dashboard.py`

### Legacy backtest

- `python run.py backtest --tickers FPT,HPG --start YYYY-MM-DD --end YYYY-MM-DD --workflows Traditional,Kelly,Markowitz`

Triggers:

- `vnstock.tools.backtest.engine.select_workflows()`
- `vnstock.tools.backtest.engine.run_portfolio_backtest()`
- automatic market-data backfill if needed via `MarketCrawler`

### Cognitive backtest

- `python run.py backtest-cognitive --tickers VN30 --start YYYY-MM-DD --end YYYY-MM-DD`

Triggers:

- `cognitive_trading.runner.CognitiveBacktestRunner`
- market-data backfill if needed

### Realtime frontend

- `cd app/frontend && npm run dev`
- `cd app/frontend && npm run build`
- `cd app/frontend && npm run start`

Triggers:

- Next.js frontend app on port `3001`

### Dashboard frontend

- `cd dashboard && npm run dev`
- `cd dashboard && npm run build`
- `cd dashboard && npm run start`

Triggers:

- Next.js dashboard on port `8000`

## 3. Globally important environment variables

`config.py` is the central environment reader. It loads `.env` from the project root and exposes config groups that are used across the repo.

### Paths and storage

- `DATA_DIR`
- `VNSTOCK_DB_PATH`
- `NEWS_DB_PATH`
- `COGNITIVE_DB_PATH`
- `MARKET_DB_PATH`
- `BACKTEST_RESULTS_DIR`
- `WORKDIR`
- `ANALYSIS_REPORTS_DIR`

These control the persistent runtime layout.

### Model and LLM routing

- `PRIMARY_MODEL`
- `FINANCIAL_MODEL`
- `NEWS_MODEL`
- `T2_MACRO`
- `T2_NEWS`
- `T2_FINANCIAL`
- `T2_TECHNICAL`
- `T2_QUANT`
- `T3_DEBATE`
- `T3_ARGUMENT`
- `T4_CIO`
- `DAILY_REPORT`
- `LLM_CONCURRENCY`
- `CLIPROXY_BASE_URL`
- `CLIPROXY_API_KEY`

These govern the agent stack and the LLM proxy configuration.

### Trading and risk controls

- `PORTFOLIO_CASH`
- `LOT_SIZE`
- `SETTLEMENT_LAG_DAYS`
- `BUY_FEE_RATE`
- `SELL_FEE_RATE`
- `MAX_TRADE_PCT`
- `MAX_BUYS_PER_TICKER`
- `PRICE_CHANGE_THRESHOLD`
- `VOL_RATIO_THRESHOLD`
- `NEWS_MIN_COUNT`
- `ALPHA_THRESHOLD`
- `SELL_THRESHOLD_OFFSET`
- `ATR_SCALE`
- `WEIGHT_ALPHA`
- `WEIGHT_BETA`
- `WEIGHT_INCREMENT_BUFFER_PCT`
- `NEWS_LOOKBACK_DAYS`
- `MAX_POSITION_PCT`
- `MAX_PORTFOLIO_INVESTED_PCT`
- `STOP_LOSS_PCT`
- `MAX_DRAWDOWN_PCT`
- `MAX_SECTOR_EXPOSURE_PCT`
- `MIN_CASH_RESERVE_PCT`
- `TRAD_TARGET_WEIGHT`
- `KELLY_MIN_WEIGHT_PCT`
- `KELLY_MAX_WEIGHT_PCT`

These matter most for backtest behavior, trading policy, and CIO/risk decisions.

### Runtime note from `run.py`

`run.py` also sets transient environment variables at runtime for news crawling:

- `NEWS_DB_PATH`
- `INGEST_DATE_FROM`
- `INGEST_DATE_TO`
- `ENABLED_SOURCES`
- `MAX_PAGES_PER_SECTION`
- `MAX_EXTRA_PAGES_PER_SECTION`

These are command-driven rather than permanent configuration.

## 4. Which dependencies belong to backend, frontend, dashboard, RAG, and cognitive trading

### Backend

From `app/backend/requirements.txt`:

- `fastapi`
- `uvicorn[standard]`
- `httpx`
- `pydantic`
- `beautifulsoup4`

From root `requirements.txt`, backend-adjacent/shared dependencies also include:

- `python-dotenv`
- `SQLAlchemy`
- `requests`
- `aiohttp`
- `pandas`
- `numpy`

### Frontend

From `app/frontend/package.json`:

- `next`
- `react`
- `react-dom`
- `react-markdown`
- `remark-gfm`
- `tailwindcss`
- `@tailwindcss/postcss`
- `eslint`
- `eslint-config-next`
- `typescript`
- `@types/node`
- `@types/react`
- `@types/react-dom`

This is the realtime UI stack.

### Dashboard

From `dashboard/package.json`:

- `next`
- `react`
- `react-dom`
- `react-markdown`
- `remark-gfm`
- `better-sqlite3`
- `lightweight-charts`
- `mermaid`
- `tailwindcss`
- `@tailwindcss/postcss`
- `eslint`
- `eslint-config-next`
- `typescript`
- `@types/node`
- `@types/react`
- `@types/react-dom`
- `@types/better-sqlite3`

This is the research/backtest visualization stack.

### RAG

From root `requirements.txt`:

- `lightrag-hku`
- `sentence-transformers`
- `faiss-cpu`
- `transformers`
- `tiktoken`

Supporting shared dependencies:

- `openai`
- `pydantic`
- `numpy`
- `pandas`

These power indexing, embeddings, retrieval, and LLM calls.

### Cognitive trading

From root `requirements.txt` and `config.py` usage:

- `pyautogen`
- `pydantic`
- `openai`
- `transformers`
- `sentence-transformers`
- `faiss-cpu`
- `cvxpy`
- `scipy`
- `scikit-learn`
- `numpy`
- `pandas`

These align with planner/swarm/debate/governance/memory style workflows and the cognitive backtest path.

### Shared quantitative/data layer

The root requirements also show the shared stock-analysis stack that supports multiple subsystems:

- `vnstock3`
- `yfinance`
- `SQLAlchemy`
- `newspaper3k`
- `beautifulsoup4`
- `lxml`
- `requests`
- `aiohttp`
- `plotly`
- `streamlit`
- `jinja2`
- `pandas-ta`

These are not owned by one single mode; they support ingestion, analysis, RAG, and reporting.

## Practical readout

- The CLI in `run.py` is the most complete operational entrypoint.
- The Next.js frontend and dashboard are separate runtime surfaces with their own npm scripts.
- The backend API is clearly present in the dependency/config surface, but its exact launch command is not defined in the files inspected here.
- `config.py` is the canonical source of runtime environment variables and filesystem locations.
- The root Python requirements file is a shared dependency bundle for agents, market data, RAG, backtesting, scraping, and visualization rather than a single service-specific lockfile.
