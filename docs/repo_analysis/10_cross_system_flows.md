# Cross-System Flows

This note ties together the main runtime paths across the repository. The same
few storage layers and artifact trees are reused by multiple subsystems, so the
important part is not just "who produces data" but also "who reads it next".

## Shared Substrates

- `data/vnstock.db` is the primary market-data store. It feeds backend price
  lookups, dashboard charts, backtests, and the analysis agents.
- `data/news.db` is the standalone news database for `tracking_news`. The
  backend usually uses the richer cache copy at `app/data/news_cache.db`.
- `data/cognitive.db` stores long-lived cognitive memory/state for the
  `cognitive_trading` layer.
- `backtest_results/` is the main artifact tree for strategy playback,
  dashboards, ledgers, reports, and cognitive run outputs.
- `vnstock/analysis_reports/` stores cached financial-analysis markdown reports
  generated from the RAG/reporting path.
- `vnstock/rag_storage/` stores the per-ticker/per-quarter LightRAG indexes.
- `app/data/` is the backend runtime workspace for JSON caches and history.

## 1) Market Data Ingestion Flow

### Entrypoints

- `run.py crawl-vnstock`
- `run.py sync` / `run.py prepare`
- Backend manual sync: `POST /api/market/sync`

### Main Modules

- `vnstock.jobs.crawler.MarketCrawler`
- `vnstock.database.models.init_db`
- `vnstock.database.repo.DataRepository`
- `app/backend/services/market_service.py`
- `app/backend/routers/market.py`

### Storage

- Primary write target: `data/vnstock.db`
- Backend memo/cache files:
  - `app/data/price_cache/today.json`
  - `app/data/price_cache/sync_flag.json`

### Output Artifacts

- Fresh OHLCV rows in `market_data_daily`
- Read-through price responses keyed by ticker
- Optional price-sync status flags for deduping repeated runs

### UI / API Touchpoints

- Backend:
  - `GET /api/market/prices`
  - `GET /api/market/news`
  - `POST /api/market/sync`
- Dashboard:
  - `GET /api/prices`
  - `GET /api/benchmark`
  - `GET /api/candles`
  - `GET /api/tickers`
- Consumers:
  - portfolio valuation
  - analysis jobs
  - backtest engines
  - charting and playback views

### Flow Notes

The ingestion path is the backbone for the rest of the system. If prices are
missing or stale, both the live analysis API and the offline backtest/dashboard
paths degrade because they all consult the same market DB.

## 2) News Ingestion Flow

### Entrypoints

- `run.py crawl-news`
- `run.py sync` / `run.py prepare`
- Backend analysis job phase 0 inside `app/backend/services/analysis_service.py`
- Backend manual sync: `POST /api/market/sync`

### Main Modules

- `tracking_news.app.ingest.run_once`
- `tracking_news.app.ingest.pipeline`
- `tracking_news.app.sources.*`
- `tracking_news.app.db.*`
- `tracking_news.app.summarizer`
- `tracking_news.app.mcp_server`
- `app/backend/services/market_service.py`
- `vnstock.tools.search_tool.SearchToolkit`
- `vnstock.agents.news_agent.NewsAgent`

### Storage

- Standalone news store: `data/news.db`
- Backend runtime cache: `app/data/news_cache.db`
- News crawl flag: `app/data/news_cache_flag.json`

### Output Artifacts

- Normalized article rows
- `article_tickers` linkage
- FTS/searchable article content
- Crawl-run metadata and dedupe state
- Summaries used by analysis agents and search helpers

### UI / API Touchpoints

- Backend:
  - `GET /api/market/news`
  - `POST /api/market/sync`
- MCP:
  - search and article lookup tools exposed by `tracking_news.app.mcp_server`
- Analysis:
  - `NewsAgent` reads the same news store
  - `SearchToolkit` resolves news lookups for agent prompts
  - backend analysis jobs crawl news before launching agents

### Flow Notes

The backend intentionally uses a richer local cache schema than the standalone
news project. That lets the analysis pipeline and agent search tools query the
same SQLite content without reimplementing the crawler.

The backend mode also patches the crawl window and limits the CafeF source set,
so it behaves more like a short-horizon signal feed than a full archival crawl.

## 3) Financial RAG Indexing and Query Flow

### Entrypoints

- `run.py rag index`
- `run.py rag query`
- `run.py rag dashboard`
- `python -m vnstock.libs.rag_engine index`
- `python -m vnstock.libs.rag_engine ask`
- `python -m vnstock.libs.rag_engine eval`

### Main Modules

- `vnstock.libs.rag_engine.ingest`
- `vnstock.libs.rag_engine.core`
- `vnstock.libs.rag_engine.retrieval`
- `vnstock.libs.rag_engine.evaluate`
- `vnstock.libs.rag_engine.dashboard`
- `vnstock.libs.rag_engine.visualize`
- `vnstock.libs.rag_engine.llm`
- `vnstock.libs.rag_engine.embedding`

### Storage

- LightRAG workspaces under `vnstock/rag_storage/<ticker>/<year>/<quarter>`
- Source OCR/text files that are indexed into the store
- Evaluation dataset: `data/golden_dataset.json`
- Evaluation outputs:
  - `ragas_report.csv`
  - `ragas_report_optimized.csv`
- Optional graph export:
  - `graph_chunk_entity_relation.graphml`
  - HTML graph visualization generated from the graph export

### Output Artifacts

- A persistent RAG index per ticker/year/quarter
- Query answers with retrieved context
- Evaluation metrics and judge-based scores
- Graph visualizations for the indexed document graph

### UI / API Touchpoints

- `run.py rag dashboard` launches the Streamlit view over RAG evaluation data
- `run.py analyze` generates cached Markdown financial reports from the
  financial reporting path, which downstream agents can reuse
- `vnstock.tools.rag_tool.FinancialRAGTool` and
  `vnstock.agents.financial_agent` consume cached report outputs

### Flow Notes

This is the repo's document-centric financial knowledge layer, not the news
index. It is used to answer questions about OCR'd reports and to generate
cached report markdown that later flows into the financial agent and the
multi-agent analysis stack.

## 4) Backend API Request Flow

### Entrypoint

- `app/backend/main.py`
- `app/backend/routers/analysis.py`
- `app/backend/routers/market.py`
- `app/backend/routers/portfolio.py`
- `app/backend/routers/history.py`

### Main Modules

- `app/backend/services/analysis_service.py`
- `app/backend/services/market_service.py`
- `app/backend/services/portfolio_service.py`
- `app/backend/services/history_service.py`
- `app/backend/bootstrap.py`

### Storage or Artifacts Used

- `app/data/history/*.json`
- `app/data/portfolio.json`
- `app/data/news_cache.db`
- `app/data/price_cache/*.json`
- `data/vnstock.db`

### Output Produced

- JSON job snapshots
- market price responses
- portfolio snapshots and valuation summaries
- persisted analysis-history records

### Downstream Consumer

- The frontend polls or fetches the API responses directly.
- The history endpoint also feeds the dashboard archive-style views.

### Flow Notes

The backend is an orchestration shell around the shared `vnstock/` and
`tracking_news/` libraries. It does not own the domain logic; it binds the live
request lifecycle to the reusable market, portfolio, news, and analysis code.

## 5) Frontend to Backend Interaction

### Entrypoint

- Frontend pages and components under `app/frontend/`
- Dashboard data pages that call the local Next.js API routes under
  `dashboard/src/app/api/*`

### Main Modules

- Frontend data-fetching hooks/components
- `dashboard/src/app/api/analysis/route.ts`
- `dashboard/src/app/api/benchmark/route.ts`
- `dashboard/src/app/api/candles/route.ts`
- `dashboard/src/app/api/prices/route.ts`
- `dashboard/src/app/api/tickers/route.ts`
- `app/backend/routers/analysis.py`
- `app/backend/routers/market.py`
- `app/backend/routers/portfolio.py`
- `app/backend/routers/history.py`

### Storage or Artifacts Used

- Live backend API responses
- `app/data/history/*.json`
- `app/data/portfolio.json`
- `data/vnstock.db`
- `backtest_results/` for replay pages

### Output Produced

- Pollable analysis jobs
- rendered portfolio state
- market/benchmark/candle payloads
- analysis report payloads

### Downstream Consumer

- The frontend UI consumes the backend API directly.
- The dashboard consumes the backend-style data model and file artifacts for
  replay and analysis screens.

### Flow Notes

The frontend is not where the analysis runs. It is the interaction layer that
starts jobs, polls for status, and renders the returned snapshots and reports.
The same UI family also reads artifact files for historical playback rather than
recomputing the runs.

## 6) Multi-Agent Analysis Flow

There are two closely related analysis flows:

1. The live backend API analysis job, which is the main user-facing workflow.
2. The offline `cognitive_trading` orchestrator, which is the research/backtest
   sibling and writes richer artifacts for playback.

### 4A. Live Backend Analysis Flow

#### Entrypoint

- Frontend POSTs `POST /api/analyze`
- Backend route: `app/backend/routers/analysis.py`
- Orchestrator: `app/backend/services/analysis_service.py`

#### Main Modules

- `app/backend/services/analysis_service.py`
- `app/backend/services/market_service.py`
- `app/backend/services/portfolio_service.py`
- `app/backend/services/history_service.py`
- `vnstock.agents.macro_agent.MacroAgent`
- `vnstock.agents.technical_agent.TechnicalAgent`
- `vnstock.agents.quant_agent.QuantAgent`
- `vnstock.agents.news_agent.NewsAgent`
- `vnstock.agents.financial_agent.FinancialAgent`
- `vnstock.workflows.traditional_scoring`
- `vnstock.workflows.kelly_criterion`
- `vnstock.workflows.markowitz_frontier`
- `cognitive_trading.decision.debate_engine.DebateEngine` for the cognitive
  workflow branch

#### Storage

- Runtime job cache: in-memory only
- Analysis history JSON: `app/data/history/*.json`
- User portfolio snapshot: `app/data/portfolio.json`
- Market data: `data/vnstock.db`
- News cache: `app/data/news_cache.db`
- Cognitive branch also touches `data/cognitive.db` through the debate and
  memory-aware modules it loads

#### Output Artifacts

- Immediate job snapshot for polling
- Per-agent outputs and inferred actions
- CIO decision per ticker
- Debate summary when the cognitive workflow is selected
- Markdown report for the final analysis
- Persisted history record with `analysis_id`

#### UI / API Touchpoints

- `POST /api/analyze`
- `GET /api/analyze/{job_id}`
- `GET /api/history`
- `GET /api/history/{analysis_id}`
- `GET /api/portfolio`
- `GET /api/portfolio/value`
- Frontend analysis page polls the job endpoint and then renders the report

#### Flow Notes

The backend analysis job is designed as a polling workflow: create job, fetch
snapshots, then store the final snapshot for historical replay. Its first phase
refreshes market and news inputs so the agents see current data before scoring.

### 6B. Offline Cognitive Trading Flow

#### Entrypoint

- `run.py backtest-cognitive`
- `cognitive_trading.runner.CognitiveBacktestRunner`

#### Main Modules

- `cognitive_trading/runner.py`
- `cognitive_trading/config.py`
- `cognitive_trading/swarm/*`
- `cognitive_trading/decision/*`
- `cognitive_trading/governance/*`
- `cognitive_trading/memory/*`
- `cognitive_trading/reporting/*`
- `cognitive_trading/analysis/*`

#### Storage

- Memory/state DB: `data/cognitive.db`
- Daily run artifacts: `backtest_results/cognitive/daily/...`
- Ledgers: `backtest_results/cognitive/ledgers/...`
- State snapshots: `backtest_results/cognitive/state/...`
- Equity curve: `backtest_results/cognitive/equity_curve.json`
- Reflection summary: `backtest_results/cognitive/reflection_summary.md`

#### Output Artifacts

- Debate transcripts and analysis cards
- CIO intent and risk-filtered actions
- Daily reports
- Equity curve and benchmark metrics
- Episodic memory and playbook promotion outputs

#### UI / API Touchpoints

- Dashboard artifact loaders read the cognitive outputs directly from disk
- `dashboard/src/lib/data.ts` maps cognitive daily artifacts into the report
  and playback views

#### Flow Notes

This path is the offline, research-oriented version of the multi-agent stack.
It is the clearest place to see memory, governance, and risk enforcement in the
repository because those concerns are explicit modules rather than being folded
into the live API job runner.

## 7) Backtest and Dashboard Artifact Flow

### Entrypoints

- `run.py backtest`
- `run.py backtest-cognitive`
- Dashboard app entry under `dashboard/src/app`

### Main Modules

- `vnstock.tools.backtest.engine.run_portfolio_backtest`
- `vnstock.tools.backtest.engine.select_workflows`
- `vnstock.tools.backtest.engine.get_latest_financial_quarter`
- `cognitive_trading.runner.CognitiveBacktestRunner`
- `dashboard/src/lib/data.ts`
- `dashboard/src/lib/summary-loader.cjs`
- `dashboard/src/lib/analysis-loader.cjs`

### Storage

- Main artifact root: `backtest_results/`
- Generic workflow playback:
  - `backtest_results/state`
  - `backtest_results/blog_posts`
  - `backtest_results/ledgers/YYYY-MM-DD`
  - `backtest_results/normalized`
- Cognitive playback:
  - `backtest_results/cognitive/state`
  - `backtest_results/cognitive/ledgers`
  - `backtest_results/cognitive/daily`
  - `backtest_results/cognitive/equity_curve.json`
  - `backtest_results/cognitive/reflection_summary.md`
- Workflow summary files:
  - `evaluation/<workflow>/summary.json`
  - optional thesis comparison file from
    `../evaluation_engine/outputs/workflow_metrics/workflow_comparison.json`

### Output Artifacts

- Daily ledgers with trade actions
- Portfolio snapshots and equity history
- Blog-style daily reports
- Normalized analysis artifacts for per-ticker views
- Benchmark and summary metrics for leaderboard-style pages
- Optional evaluation overrides for thesis comparison

### UI / API Touchpoints

- Dashboard pages and components:
  - leaderboard
  - portfolio playback
  - trading-view style charts
  - agents / analysis report views
  - blog/report archive
- Dashboard API routes backed by the live market DB:
  - `GET /api/analysis`
  - `GET /api/benchmark`
  - `GET /api/candles`
  - `GET /api/candles-debug`
  - `GET /api/prices`
  - `GET /api/tickers`

### Flow Notes

The dashboard does not compute the backtests itself. It is a file-backed reader
for the artifact tree produced by the backtest and cognitive runners. That makes
the playback experience reproducible and lets the UI render the same run long
after the process that created it has exited.

## End-to-End Dependency Graph

The flows connect like this:

- Market ingestion writes `data/vnstock.db`.
- News ingestion writes `data/news.db` or `app/data/news_cache.db`.
- Financial RAG writes `vnstock/rag_storage/...` and cached report markdown.
- The live backend analysis job reads market/news/portfolio inputs, calls the
  five agents, writes `app/data/history/*.json`, and returns a report to the UI.
- The offline cognitive runner writes `data/cognitive.db` plus
  `backtest_results/cognitive/...`.
- The dashboard reads the artifact tree and the live market DB to render
  history, playback, charting, and report views.

In practice, `data/vnstock.db`, `app/data/news_cache.db`, `app/data/history/`,
`data/cognitive.db`, and `backtest_results/` are the main cross-system handoff
points.
