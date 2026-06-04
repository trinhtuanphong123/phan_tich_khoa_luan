# README vs Actual Repository

This note compares the top-level README and early repo map against the modules
actually inspected in the codebase. The main pattern is that the README gives a
useful high-level story, but it compresses several distinct subsystems into one
smooth narrative. That makes it easy for a new developer to miss how much of the
repo is file-backed, how many layers are separate, and which parts are only
partially present in source.

## 1) Features or subsystems described in README but not clearly implemented

### Evaluation / thesis / LLM-as-judge

- The README presents a full "Thesis/evaluation" capability with diagnostics,
  workflow metrics, and LLM-as-judge.
- In the analyzed checkout, there is no `evaluation_engine/` source folder.
- The dashboard only references an external artifact contract at
  `evaluation_engine/outputs/workflow_metrics/workflow_comparison.json`.
- Result: the README overstates the presence of an in-repo evaluation subsystem.
  What exists in source is an output-consumer contract, not a visible producer.

### One unified app shell

- The README reads like a single product with one realtime app.
- In reality there are multiple distinct execution surfaces:
  - `run.py` CLI
  - `app/backend` FastAPI API
  - `app/frontend` realtime UI
  - `dashboard` artifact playback UI
  - `tracking_news` ingestion/search package
  - `cognitive_trading` offline orchestration layer
  - `vnstock/libs/rag_engine` RAG CLI and dashboard
- Result: the README is directionally correct, but it hides the degree of
  subsystem independence.

### News intelligence as a direct standalone store

- The README says news is crawled into `data/news.db` and used for agent
  analysis.
- In the live backend path, the code typically uses the richer
  `app/data/news_cache.db` cache and patches `tracking_news` behavior before
  crawling.
- Result: the README is true for the standalone subsystem, but not precise
  enough for the backend runtime path.

## 2) Implemented subsystems that are under-described in README

### Backend API orchestration

- The README mentions the realtime UI, but it does not clearly spell out the
  backend service layer.
- Actual source includes:
  - `app/backend/main.py`
  - `app/backend/routers/analysis.py`
  - `app/backend/services/analysis_service.py`
  - `app/backend/services/market_service.py`
  - `app/backend/services/portfolio_service.py`
  - `app/backend/services/history_service.py`
- These modules define the real request flow, job polling behavior, portfolio
  persistence, history persistence, and market/news cache access.

### File-backed dashboard loaders

- The README says the dashboard shows leaderboard, portfolio playback, trading
  view, and reports.
- The actual implementation is more specific: `dashboard/src/lib/data.ts` reads
  several artifact layouts, including legacy layouts, cognitive daily runs, and
  workflow summaries.
- Result: the artifact-contract complexity is under-described.

### Cognitive trading internals

- The README mentions planner, swarm, debate engine, governance, memory, and
  daily reporting.
- The actual `cognitive_trading/` package contains a richer split:
  - `runner.py`
  - `swarm/`
  - `decision/`
  - `governance/`
  - `memory/`
  - `reporting/`
- The code also persists artifacts to `backtest_results/cognitive/` and memory
  to `data/cognitive.db`.
- Result: the README captures the concept but not the persistence model or the
  artifact layout.

### Financial RAG evaluation and visualization

- The README explains indexing and querying financial OCR reports.
- The actual RAG stack also includes:
  - evaluation metrics and judge-style scoring
  - graph visualization export
  - dashboard support for report inspection
  - report caching that downstream agents reuse
- Result: the README under-describes the evaluation and visualization branches.

### Tracking news MCP server

- The README says news can be searched and used by agents, but it does not call
  out the MCP server surface.
- The source exposes `tracking_news.app.mcp_server`, which is a separate access
  path from the backend API.
- Result: the README underplays the fact that `tracking_news` is not only a
  crawler, but also a query-serving module.

## 3) Likely renamed, merged, deprecated, or partially implemented areas

### `evaluation_engine`

- Likely the clearest partially externalized area.
- It is referenced by the dashboard, but the folder is absent in this checkout.
- The repository appears to depend on evaluation artifacts produced elsewhere or
  in a missing branch/submodule.

### `sync` / `prepare`

- `run.py` uses `sync` and `prepare` as aliases for a merged orchestration flow
  that does:
  - market price sync
  - news crawl
  - cached financial report generation
- This is not a single domain operation; it is a convenience umbrella command.

### Traditional / Kelly / Markowitz / Cognitive

- The README lists the workflows, but the code suggests they are successive
  generations of the same analysis pipeline:
  - traditional scoring
  - Kelly criterion
  - Markowitz frontier
  - cognitive debate-based workflow
- The cognitive branch is the most structurally distinct and is the only one
  that clearly routes through debate and memory-aware logic.

### Standalone news DB vs backend news cache

- `data/news.db` and `app/data/news_cache.db` are both real, but they serve
  different layers.
- This split looks like an adaptation/merge point rather than a single canonical
  news store.

## 4) Places where documentation may mislead a new developer

### The README suggests one clean end-to-end product

- In practice, the repo is a federation of subsystems connected by shared
  SQLite files and generated artifacts.
- A new developer may assume direct in-memory coupling where the actual design
  is file-backed.

### The README is not explicit about producer vs consumer roles

- Many components are readers only:
  - dashboard loads artifacts
  - backend reads and writes caches/history
  - agents read market/news/RAG data
- Without reading the code, it is easy to assume every subsystem is both a
  producer and a consumer in the same way.

### `run.py analyze` is not the same as live API analysis

- The CLI analysis command generates cached financial reports.
- The live analysis API is a job-based multi-agent orchestration flow.
- The README mentions both, but they can be mistaken for the same feature.

### `app/start_backend.py` is easy to miss

- The README's quick start suggests a backend launch step, but the actual
  robust launcher is `app/start_backend.py`.
- The low-level backend app lives in `app/backend/main.py`.
- A newcomer may try to start the wrong file if they only follow the prose.

### The dashboard is more file-driven than the README implies

- The dashboard reads:
  - `backtest_results/`
  - `data/vnstock.db`
  - `evaluation/<workflow>/summary.json`
  - `backtest_results/cognitive/...`
- It is not just a "visual frontend"; it is a replay tool for artifact trees.

### The repo map is too shallow to resolve subsystem boundaries

- `docs/repo_analysis/00_repo_map.md` is useful for top-level orientation, but
  it intentionally avoids deeper traversal.
- A new developer using only that map will miss:
  - backend service boundaries
  - news cache vs standalone news DB split
  - dashboard artifact loading behavior
  - cognitive memory/governance layout
  - RAG evaluation and visualization branches

## Bottom line

The README is accurate at the slogan level, but it smooths over several
important implementation boundaries:

- live API vs offline artifact playback
- standalone news ingestion vs backend news cache
- report RAG vs query/evaluation/graph tooling
- normal multi-agent analysis vs cognitive orchestration
- source code vs external evaluation artifacts

For a new developer, the safest reading assumption is:

1. `run.py` is the command router.
2. `app/backend` is the live API shell.
3. `vnstock/` contains the reusable trading/analysis library.
4. `tracking_news/` is a separate ingestion/search subsystem.
5. `cognitive_trading/` is the offline orchestration layer.
6. `dashboard/` is a file-backed replay UI, not a compute engine.

