# Human Reading Order

This is the recommended sequence for a new developer who wants to understand
the repository without getting lost in implementation details too early. The
order moves from intent to runtime shape, then into the main code paths, then
into the subsystems that produce and consume artifacts.

## 1) First 30 Minutes

Read these first:

1. [`docs/repo_analysis/00b_repo_goal_and_modes.md`](./00b_repo_goal_and_modes.md)
2. [`docs/repo_analysis/01_runtime_and_entrypoints.md`](./01_runtime_and_entrypoints.md)
3. [`docs/repo_analysis/02_runpy_command_map.md`](./02_runpy_command_map.md)
4. [`docs/repo_analysis/03_config_spine.md`](./03_config_spine.md)
5. [`README.md`](/D:/TradingAgent-VN/README.md)

Why this order:

- `00b_repo_goal_and_modes.md` tells you what the repository is trying to do at
  a high level.
- `01_runtime_and_entrypoints.md` shows how the repo starts and which runtime
  modes actually exist.
- `02_runpy_command_map.md` gives the operational command tree for `run.py`.
- `03_config_spine.md` explains the shared configuration and path model.
- `README.md` is useful after the analysis docs because you can now see where it
  is precise and where it is aspirational.

What you should understand by the end:

- the repository's purpose
- the major runtime modes
- which paths and environment variables matter globally
- which subsystems are meant to be primary vs supporting

## 2) First 2 Hours

Read these next:

1. [`run.py`](/D:/TradingAgent-VN/run.py)
2. [`config.py`](/D:/TradingAgent-VN/config.py)
3. [`app/backend/main.py`](/D:/TradingAgent-VN/app/backend/main.py)
4. [`app/backend/routers/analysis.py`](/D:/TradingAgent-VN/app/backend/routers/analysis.py)
5. [`app/backend/services/analysis_service.py`](/D:/TradingAgent-VN/app/backend/services/analysis_service.py)
6. [`app/backend/services/market_service.py`](/D:/TradingAgent-VN/app/backend/services/market_service.py)
7. [`app/backend/services/portfolio_service.py`](/D:/TradingAgent-VN/app/backend/services/portfolio_service.py)
8. [`app/backend/services/history_service.py`](/D:/TradingAgent-VN/app/backend/services/history_service.py)
9. [`docs/repo_analysis/05_app_backend.md`](./05_app_backend.md)
10. [`docs/repo_analysis/06_app_frontend.md`](./06_app_frontend.md)
11. [`dashboard/src/lib/data.ts`](/D:/TradingAgent-VN/dashboard/src/lib/data.ts)
12. [`dashboard/src/app/api/analysis/route.ts`](/D:/TradingAgent-VN/dashboard/src/app/api/analysis/route.ts)
13. [`dashboard/src/app/api/prices/route.ts`](/D:/TradingAgent-VN/dashboard/src/app/api/prices/route.ts)

Why this order:

- `run.py` is the command dispatcher; it shows how the main workflows enter the
  codebase.
- `config.py` confirms the shared storage and model settings.
- `app/backend/main.py` shows how the live API is assembled.
- The backend route and service files show the request lifecycle, data caching,
  and persistence model.
- The frontend and dashboard files show how requests and artifacts are consumed
  back out.

What you should understand by the end:

- how market, news, portfolio, and analysis requests move through the backend
- how the live UI talks to the backend
- how the dashboard loads market data and replay artifacts
- where live requests end and file-backed playback begins

## 3) First Half Day

Read these next:

1. [`vnstock/`](./04_vnstock_core.md)
2. [`docs/repo_analysis/04_vnstock_core.md`](./04_vnstock_core.md)
3. [`vnstock/libs/rag_engine/ingest.py`](/D:/TradingAgent-VN/vnstock/libs/rag_engine/ingest.py)
4. [`vnstock/libs/rag_engine/retrieval.py`](/D:/TradingAgent-VN/vnstock/libs/rag_engine/retrieval.py)
5. [`vnstock/libs/rag_engine/evaluate.py`](/D:/TradingAgent-VN/vnstock/libs/rag_engine/evaluate.py)
6. [`tracking_news/app/ingest/run_once.py`](/D:/TradingAgent-VN/tracking_news/app/ingest/run_once.py)
7. [`tracking_news/app/ingest/pipeline.py`](/D:/TradingAgent-VN/tracking_news/app/ingest/pipeline.py)
8. [`tracking_news/app/mcp_server.py`](/D:/TradingAgent-VN/tracking_news/app/mcp_server.py)
9. [`docs/repo_analysis/07_tracking_news.md`](./07_tracking_news.md)
10. [`cognitive_trading/runner.py`](/D:/TradingAgent-VN/cognitive_trading/runner.py)
11. [`cognitive_trading/decision/debate_engine.py`](/D:/TradingAgent-VN/cognitive_trading/decision/debate_engine.py)
12. [`cognitive_trading/governance/schemas.py`](/D:/TradingAgent-VN/cognitive_trading/governance/schemas.py)
13. [`cognitive_trading/memory/db.py`](/D:/TradingAgent-VN/cognitive_trading/memory/db.py)
14. [`docs/repo_analysis/08_cognitive_trading.md`](./08_cognitive_trading.md)
15. [`dashboard/src/lib/summary-loader.cjs`](/D:/TradingAgent-VN/dashboard/src/lib/summary-loader.cjs)

Why this order:

- `vnstock/` is the reusable library layer that most other subsystems depend on.
- The RAG files explain the financial-document retrieval path and how report
  indexing/querying works.
- `tracking_news` explains the standalone news subsystem that the backend and
  agents reuse.
- `cognitive_trading` is the deeper orchestration layer with memory,
  governance, and debate.
- The dashboard summary loader shows how cross-run summary artifacts are
  consumed.

What you should understand by the end:

- how the reusable library layer is structured
- how financial RAG differs from news crawling
- how the news subsystem is both a crawler and a query surface
- how the cognitive workflow turns agent outputs into decisions and durable
  memory
- how summary artifacts feed the dashboard

## 4) Full Day Deep Dive

Read these next:

1. [`docs/repo_analysis/09_dashboard.md`](./09_dashboard.md)
2. [`dashboard/src/app/`](./dashboard/src/app)
3. [`dashboard/src/components/`](./dashboard/src/components)
4. [`dashboard/src/lib/analysis-loader.cjs`](/D:/TradingAgent-VN/dashboard/src/lib/analysis-loader.cjs)
5. [`docs/repo_analysis/10_cross_system_flows.md`](./10_cross_system_flows.md)
6. [`docs/repo_analysis/10_evaluation_engine.md`](./10_evaluation_engine.md)
7. [`docs/repo_analysis/11_readme_vs_actual.md`](./11_readme_vs_actual.md)
8. [`docs/repo_analysis/README_CODEBASE.md`](./README_CODEBASE.md)

Why this order:

- `09_dashboard.md` explains the dashboard as a file-backed research UI.
- The dashboard source folders are where the route/page/component boundaries are
  clearest.
- `analysis-loader.cjs` and `summary-loader.cjs` reveal how artifact formats are
  normalized and how legacy layouts are still supported.
- `10_cross_system_flows.md` ties all subsystems together end-to-end.
- `10_evaluation_engine.md` is last because it records an external or missing
  contract rather than a visible source tree.
- `11_readme_vs_actual.md` is useful after you know the implementation because
  it tells you where the README is accurate and where it is misleading.
- `README_CODEBASE.md` works best after the deeper reading because it is a
  consolidated orientation rather than a source-of-truth for details.

What you should understand by the end:

- how the dashboard reconstructs runs from artifact trees
- how the repository's subsystems connect through SQLite and generated files
- where the docs are accurate, incomplete, or aspirational
- which pieces are likely to be refactored first if the repo is simplified

## Suggested Shortest Path

If you only want the highest-value subset, read:

1. `00b_repo_goal_and_modes.md`
2. `01_runtime_and_entrypoints.md`
3. `02_runpy_command_map.md`
4. `03_config_spine.md`
5. `run.py`
6. `app/backend/services/analysis_service.py`
7. `dashboard/src/lib/data.ts`
8. `tracking_news/app/ingest/pipeline.py`
9. `cognitive_trading/runner.py`
10. `10_cross_system_flows.md`

