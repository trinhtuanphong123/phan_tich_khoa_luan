# Human Reading Order

This is the shortest path to understanding the repository without reading
everything in source order. The sequence starts with the repo-level intent and
runtime surface, then moves into the live API and library code, then into the
offline subsystems and artifact consumers.

## 1) First Hour

Read these first to build the mental model of what the repo is for and how it
starts:

1. [`docs/repo_analysis/00b_repo_goal_and_modes.md`](./00b_repo_goal_and_modes.md)
2. [`docs/repo_analysis/01_runtime_and_entrypoints.md`](./01_runtime_and_entrypoints.md)
3. [`docs/repo_analysis/02_runpy_command_map.md`](./02_runpy_command_map.md)
4. [`docs/repo_analysis/03_config_spine.md`](./03_config_spine.md)
5. [`run.py`](/D:/TradingAgent-VN/run.py)
6. [`config.py`](/D:/TradingAgent-VN/config.py)
7. [`app/backend/main.py`](/D:/TradingAgent-VN/app/backend/main.py)

Why this order:

- The first four docs tell you what the repository is trying to do, how it
  launches, and which commands matter.
- `run.py` is the top-level dispatch surface, so it anchors every operational
  mode.
- `config.py` is the shared path-and-model spine used across subsystems.
- `app/backend/main.py` shows the live API bootstrap and which routers define
  the user-facing backend.

## 2) Half Day

Read these next to understand the two core day-to-day surfaces: the backend API
and the main reusable library stack that powers it.

1. [`docs/repo_analysis/04_vnstock_core.md`](./04_vnstock_core.md)
2. [`docs/repo_analysis/05_app_backend.md`](./05_app_backend.md)
3. [`app/backend/routers/analysis.py`](/D:/TradingAgent-VN/app/backend/routers/analysis.py)
4. [`app/backend/services/analysis_service.py`](/D:/TradingAgent-VN/app/backend/services/analysis_service.py)
5. [`app/backend/services/market_service.py`](/D:/TradingAgent-VN/app/backend/services/market_service.py)
6. [`app/backend/services/history_service.py`](/D:/TradingAgent-VN/app/backend/services/history_service.py)
7. [`app/backend/services/portfolio_service.py`](/D:/TradingAgent-VN/app/backend/services/portfolio_service.py)
8. [`docs/repo_analysis/06_app_frontend.md`](./06_app_frontend.md)
9. [`dashboard/src/lib/data.ts`](/D:/TradingAgent-VN/dashboard/src/lib/data.ts)
10. [`dashboard/src/app/api/analysis/route.ts`](/D:/TradingAgent-VN/dashboard/src/app/api/analysis/route.ts)
11. [`dashboard/src/app/api/prices/route.ts`](/D:/TradingAgent-VN/dashboard/src/app/api/prices/route.ts)

Why this order:

- `vnstock` is the shared business-logic layer, so it should come before the
  backend details that orchestrate it.
- The backend docs and service files explain how live requests move through the
  system, what gets cached, and what gets persisted.
- The frontend doc and the dashboard data loader show how the UI reads the same
  data back out of SQLite, JSON caches, and backtest artifacts.
- The dashboard API routes are the concrete bridge between UI and local data
  stores.

## 3) Full Day

Read these when you want the supporting subsystems, offline research flows, and
artifact consumers that complete the picture.

1. [`docs/repo_analysis/07_tracking_news.md`](./07_tracking_news.md)
2. [`tracking_news/app/ingest/run_once.py`](/D:/TradingAgent-VN/tracking_news/app/ingest/run_once.py)
3. [`tracking_news/app/ingest/pipeline.py`](/D:/TradingAgent-VN/tracking_news/app/ingest/pipeline.py)
4. [`tracking_news/app/mcp_server.py`](/D:/TradingAgent-VN/tracking_news/app/mcp_server.py)
5. [`docs/repo_analysis/08_cognitive_trading.md`](./08_cognitive_trading.md)
6. [`cognitive_trading/runner.py`](/D:/TradingAgent-VN/cognitive_trading/runner.py)
7. [`cognitive_trading/decision/debate_engine.py`](/D:/TradingAgent-VN/cognitive_trading/decision/debate_engine.py)
8. [`cognitive_trading/governance/schemas.py`](/D:/TradingAgent-VN/cognitive_trading/governance/schemas.py)
9. [`cognitive_trading/memory/db.py`](/D:/TradingAgent-VN/cognitive_trading/memory/db.py)
10. [`docs/repo_analysis/09_dashboard.md`](./09_dashboard.md)
11. [`dashboard/src/lib/summary-loader.cjs`](/D:/TradingAgent-VN/dashboard/src/lib/summary-loader.cjs)
12. [`dashboard/src/lib/analysis-loader.cjs`](/D:/TradingAgent-VN/dashboard/src/lib/analysis-loader.cjs)
13. [`docs/repo_analysis/10_cross_system_flows.md`](./10_cross_system_flows.md)
14. [`docs/repo_analysis/10_evaluation_engine.md`](./10_evaluation_engine.md)

Why this order:

- `tracking_news` comes after the backend because it is a supporting content
  ingestion subsystem, not the main application shell.
- `cognitive_trading` follows because it is the deepest orchestration layer
  and the clearest place to study memory, governance, and decision synthesis.
- The dashboard artifact loaders come after the producers so you can see how
  the UI reconstructs runs from disk.
- The cross-system flow note is most valuable once you already know the pieces.
- `evaluation_engine` is last because the repository snapshot does not include
  the folder itself; the doc records only the artifact contract the dashboard
  expects.

## Practical Shortcut

If you want a single pass with the highest return, read in this order:

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
