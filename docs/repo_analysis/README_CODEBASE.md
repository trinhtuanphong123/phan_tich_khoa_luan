# Codebase Overview

This repository is a Vietnamese stock-analysis system that combines market data
ingestion, news ingestion, financial-document RAG, multi-agent analysis,
backtesting, and a dashboard for replaying artifacts and results. It is not one
single app; it is a set of cooperating subsystems that exchange data mostly
through SQLite databases, JSON artifacts, and markdown reports.

The project is not a single app with one clean execution path. It is a set of
connected subsystems that share a few key stores:

- `data/vnstock.db` for market prices and price history
- `data/news.db` for standalone news ingestion
- `app/data/` for backend runtime caches and analysis history
- `data/cognitive.db` for cognitive trading memory/state
- `backtest_results/` for produced artifacts and playback data
- `vnstock/rag_storage/` for document-index storage

## 1) Repository Purpose

The repository exists to support stock research and decision-making workflows:

- ingest and query market data
- ingest and search financial/news content
- generate analyst-style reports
- run portfolio backtests
- run a cognitive multi-agent orchestration layer
- render the resulting artifacts in a dashboard

The strongest pattern in the codebase is "produce structured artifacts, then
read them back later for analysis or UI playback."

## 2) Main Subsystems

### Core runtime / CLI

- `run.py` is the top-level command dispatcher.
- It exposes the main operational modes:
  - market data crawl/sync
  - news crawl
  - financial analysis generation
  - RAG indexing/querying/dashboard
  - backtest
  - cognitive backtest
  - full sync / prepare flow

### Shared business logic

- `vnstock/` contains the reusable trading and analysis library layer.
- This includes:
  - market data access
  - agents
  - workflows
  - financial report generation
  - backtest engine
  - RAG engine
  - search utilities

### Backend API

- `app/backend/` is the live API surface.
- It exposes:
  - analysis jobs
  - market data access
  - portfolio CRUD/value
  - history replay
- It acts as the runtime bridge between frontend requests and the shared
  business-logic layer.
- `app/start_backend.py` is the practical launcher for this API.

### Frontend UI

- `app/frontend/` is the realtime UI.
- It talks to the backend API for live analysis, portfolio, and market data.
- It is the interaction layer for starting jobs and rendering live snapshots.

### News subsystem

- `tracking_news/` is a separate ingestion/search subsystem.
- It provides:
  - crawling
  - normalization
  - SQLite storage
  - an MCP server
  - a Streamlit dashboard

### Cognitive trading subsystem

- `cognitive_trading/` is the orchestration layer for the deeper multi-agent
  cognitive workflow.
- It contains:
  - planner / swarm / debate / CIO logic
  - memory
  - governance / risk enforcement
  - reporting
  - backtest-oriented run orchestration

### Dashboard

- `dashboard/` is the artifact playback and research dashboard.
- It reads from `backtest_results/`, the market DB, and summary files rather
  than recomputing the workflows itself.
- It is primarily a consumer of artifacts, not a computation engine.

### Evaluation contract

- `evaluation_engine/` is not present in this checkout.
- The dashboard still expects an output contract from that system when present,
  especially for workflow-comparison metrics.
- Treat this as an external or missing subsystem, not a visible source tree.

## 3) Main Entrypoints

### Top-level CLI

- `run.py`

### Backend

- `app/backend/main.py`

### Frontend

- `app/frontend` package entrypoints and routes

### News

- `tracking_news/app/ingest/run_once.py`
- `tracking_news/app/mcp_server.py`
- `tracking_news/apps/dashboard_streamlit.py`

### Cognitive trading

- `cognitive_trading/runner.py`

### RAG

- `vnstock/libs/rag_engine/__main__.py`
- `vnstock/libs/rag_engine/cli.py`

### Dashboard

- `dashboard/src/app/*`
- `dashboard/src/lib/*`

## 4) Main Data Stores

### `data/vnstock.db`

Primary market database. Used by:

- market sync
- backend price lookup
- benchmark lookup
- dashboard charts
- backtest data selection
- agent price context

### `data/news.db`

Standalone news database from `tracking_news`.

### `app/data/news_cache.db`

Backend runtime news cache. It is usually the news DB consumed by the live API
analysis path.

### `app/data/history/`

JSON history records for completed analysis jobs.

### `app/data/portfolio.json`

Current portfolio snapshot for the live backend workflow.

### `data/cognitive.db`

SQLite memory/state store for the cognitive trading layer.

### `backtest_results/`

Produced run artifacts:

- ledgers
- state snapshots
- blog posts / daily reports
- normalized workflow artifacts
- cognitive daily artifacts
- equity curves
- benchmark metrics

### `vnstock/rag_storage/`

LightRAG storage tree organized by ticker/year/quarter.

### `vnstock/analysis_reports/`

Cached Markdown financial reports created by the analysis/reporting path.

## 5) How the Pieces Fit Together

The flow is best understood as a pipeline of shared stores and readers:

1. Market data is ingested into `data/vnstock.db`.
2. News is ingested into `data/news.db` or `app/data/news_cache.db`.
3. Financial documents are indexed into `vnstock/rag_storage/`.
4. `run.py` and the backend API call into `vnstock/`, `tracking_news/`, and
   `cognitive_trading/` to produce analysis outputs.
5. Live analysis jobs persist history JSON into `app/data/history/`.
6. Cognitive runs persist deeper artifacts into `backtest_results/cognitive/`
   and memory into `data/cognitive.db`.
7. The dashboard reads the artifact tree, summary JSON, and the market DB to
   reconstruct portfolio playback, reports, and charts.

The important architectural idea is that most subsystems are not tightly wired
together by direct imports alone. They are also coupled through file-based
artifacts and SQLite stores.

## 6) Common Confusion Points

### 1. `tracking_news` vs `app/backend/services/market_service.py`

- `tracking_news` is the real ingestion subsystem.
- `market_service` is a backend wrapper that patches and reuses parts of
  `tracking_news` to produce a smaller cache for live analysis.

### 2. `data/news.db` vs `app/data/news_cache.db`

- `data/news.db` is the standalone news store.
- `app/data/news_cache.db` is the backend cache copy that the live API usually
  uses.

### 3. `run.py analyze` vs backend `/api/analyze`

- `run.py analyze` is the CLI path for generating a cached financial report.
- `POST /api/analyze` is the live multi-agent analysis job API.

### 4. `backtest_results/` vs `data/*`

- `data/*` stores persistent inputs and memory.
- `backtest_results/` stores outputs and replayable artifacts.

### 5. Dashboard is mostly a reader, not a producer

- The dashboard does not compute the backtests or the cognitive runs.
- It reconstructs views from the artifacts that other subsystems already wrote.

### 6. There are two multi-agent layers

- The backend API has a job-based multi-agent analysis flow for interactive use.
- `cognitive_trading/` is the richer offline orchestration layer for research
  and backtest-style runs.

### 7. Evaluation engine is referenced, not present

- Some dashboard code expects evaluation outputs under
  `evaluation_engine/outputs/workflow_metrics/`.
- The source folder is absent in this checkout, so treat it as an external or
  missing dependency contract.

### 8. The same feature often exists in two layers

- Some behaviors exist once as live API/service code and again as artifact
  readers:
  - analysis job vs analysis playback
  - news DB vs news cache DB
  - backtest producer vs dashboard consumer
- If a new developer misses this split, they will misread the architecture.

## 7) Recommended Next Actions for Refactor or Simplification

If the goal is to simplify the codebase, the best next steps are:

### 1. Separate "producer" and "consumer" boundaries

- Make it explicit which modules write artifacts and which only read them.
- This is especially useful for `backtest_results/`, `app/data/`, and
  `data/cognitive.db`.

### 2. Normalize the data contracts

- Define stable schemas for:
  - analysis job snapshots
  - ledger entries
  - cognitive daily artifacts
  - news article records
  - summary files
- This will reduce the amount of path-specific and format-specific code in the
  dashboard and backend loaders.

### 3. Reduce duplicate market/news access logic

- The backend, agents, and dashboard all read market data in slightly different
  ways.
- Consolidating the read path around a single repository/API layer would reduce
  drift.

### 4. Clarify the two analysis stacks

- Keep the live API analysis job and the cognitive offline runner clearly
  separated in naming, storage, and docs.
- Right now they are conceptually similar enough to confuse a new developer.

### 5. Isolate artifact loading in the dashboard

- The dashboard currently knows about many historical layouts and legacy paths.
- A small artifact-adapter layer would make it easier to migrate formats without
  touching every page.

### 6. Make `tracking_news` integration explicit

- The backend currently monkey-patches parts of `tracking_news` to get the
  desired crawl window and source subset.
- That works, but it is brittle. A parameterized crawl API would be easier to
  maintain.

### 7. Keep the RAG and financial-report paths distinct

- The repository has both a document RAG index and a cached financial report
  generation path.
- They are related, but they solve different problems and should stay clearly
  separated.

### 8. Decide whether the external evaluation contract should become first-class

- If evaluation remains important, either add the missing `evaluation_engine/`
  source tree or document the external artifact contract as an intentional
  boundary.
- If it is no longer needed, remove the stale references from the dashboard and
  README.

## 8) Suggested Reading Sequence

If you want to go from zero to productive quickly:

1. `docs/repo_analysis/00b_repo_goal_and_modes.md`
2. `docs/repo_analysis/01_runtime_and_entrypoints.md`
3. `docs/repo_analysis/02_runpy_command_map.md`
4. `docs/repo_analysis/03_config_spine.md`
5. `run.py`
6. `app/backend/main.py`
7. `app/backend/services/analysis_service.py`
8. `dashboard/src/lib/data.ts`
9. `cognitive_trading/runner.py`
10. `tracking_news/app/ingest/run_once.py`
