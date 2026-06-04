# Repo Goal and Operating Modes

## 1. What this repository is trying to do

`TradingAgent-VN` is a workspace and demo for an AI trading system focused on the Vietnam stock market. The README describes it as an AI hedge-fund style, multi-agent stock analysis platform that:

- crawls market data and financial news
- indexes financial report OCR text for retrieval-augmented analysis
- runs multiple specialist agents in parallel
- produces trading or investment recommendations
- supports simulation/backtesting and research dashboards

In short, the repository is trying to combine data collection, financial analysis, RAG over reports, agent-based decision making, and visualization into one end-to-end research and demo environment.

## 2. Main operating modes

### CLI

The root entrypoint is `run.py`. The README shows it as the main operational interface for:

- crawling stock data
- crawling news
- syncing data
- generating financial analysis reports
- indexing/querying RAG content
- running legacy backtests
- running cognitive backtests

This is the most complete control surface for the project.

### Backend API

The `app/` folder contains a FastAPI backend. The README shows it serving API endpoints such as:

- `/api/health`
- `/api/market/prices`
- `/api/portfolio/value`

This backend supports the realtime application and exposes portfolio, market, analysis, and history data.

### Frontend UI

The realtime frontend lives in `app/frontend/` and is a Next.js application. It is described as the interactive UI for:

- selecting tickers
- selecting workflows
- running analysis
- viewing agent cards
- viewing CIO summaries and Markdown reports

It is the user-facing app for live interaction with the backend.

### Dashboard

The `dashboard/` app is a separate Next.js research/backtest dashboard. The README says it reads:

- `backtest_results/`
- `data/vnstock.db`

It focuses on research presentation rather than live analysis, with views like leaderboard, portfolio playback, charting, and report pages.

### Crawlers

There are at least two data-ingestion paths described in the README:

- market data crawling via `crawl-vnstock`
- news crawling via `crawl-news`

These feed the core databases and make the rest of the system useful.

### RAG

Financial RAG is a first-class mode. It indexes OCR text from financial reports and supports query modes:

- `global`
- `local`
- `hybrid`

The README also shows a dedicated RAG dashboard command. This subsystem exists to let the financial agent answer questions over report text.

### Backtest

Backtesting is another major mode. The README distinguishes:

- legacy workflows: Traditional Scoring, Kelly Criterion, Markowitz Frontier
- cognitive backtesting: Cognitive Swarm

Backtest output is written to `backtest_results/` and is used by the dashboard.

### Cognitive trading

The cognitive trading subsystem is a more advanced workflow centered on:

- planner
- analyst swarm
- debate engine
- governance and risk
- memory
- daily reporting

The README presents this as a dedicated workflow and also exposes it as `backtest-cognitive` and as a module entrypoint under `cognitive_trading.runner`.

## 3. Primary mode vs supporting subsystems

### Primary

The primary mode appears to be the combined AI trading/research pipeline exposed through the root CLI and the realtime app:

- data ingestion
- analysis
- multi-agent reasoning
- reporting
- decision support

If I had to name one center of gravity, it is the `run.py` + `vnstock/` + `app/` stack that powers the end-to-end trading analysis workflow.

### Supporting subsystems

These look like supporting layers around the core analysis pipeline:

- crawlers for market and news data
- Financial RAG for report retrieval
- backtesting for evaluation
- the dashboard for research visualization
- the cognitive trading package as a specialized higher-order workflow
- evaluation/thesis materials as research support

Those subsystems are important, but they mostly serve the main analysis and decision pipeline rather than replacing it.

## 4. Data stores and artifacts the system depends on

### Persistent data stores

- `data/vnstock.db` for market OHLCV and related stock data
- `data/news.db` for crawled news
- `data/cognitive.db` for cognitive-trading memory/state
- `app/data/` for runtime portfolio/history/cache data
- `vnstock/rag_storage/<TICKER>/<YEAR>/<QUARTER>/` for indexed RAG storage
- `backtest_results/` for backtest ledgers, states, normalized artifacts, and reports

### Financial-report inputs

- `vnstock/libs/data/financial_reports/*.ocr_text.txt`
- `vnstock/libs/data/financial_reports/*.pdf`

These are the source artifacts for Financial RAG.

### Generated outputs

- `vnstock/analysis_reports/<TICKER>_<YEAR>_Q<n>.md` for generated financial analysis reports
- dashboard-readable artifacts under `backtest_results/`

### Configuration artifacts

- `.env` for runtime secrets and path settings
- `.env.example` as the public template
- `config.py` as the central config loader

### Dependency on external services

The README also implies dependency on:

- an OpenAI-compatible LLM endpoint/API key
- Node.js dependencies for the Next.js apps
- SQLite as the storage layer

That is the minimum picture the README and top-level structure provide.
