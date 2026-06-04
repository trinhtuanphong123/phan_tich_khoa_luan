# `vnstock` Core Architecture

This note analyzes only the `vnstock/` folder.

## 1. Important subfolders and responsibilities

### `vnstock/database`

Persistent storage layer.

- `models.py` defines the SQLite schema and DB initialization.
- `repo.py` is the main data access layer for market data, financial ratios, symbol metadata, sentiment, and agent logs.

### `vnstock/jobs`

Ingestion and batch jobs.

- `crawler.py` syncs market data and financial ratios into SQLite.
- `news_processor.py` turns crawled news into daily sentiment rows.

### `vnstock/agents`

Domain analysis agents.

- `macro_agent.py` analyzes macro/news context.
- `news_agent.py` analyzes company-specific news.
- `technical_agent.py` analyzes chart/price structure.
- `quant_agent.py` computes quantitative alpha and wraps it in an LLM-facing report.
- `financial_agent.py` serves cached financial report context and can generate one when needed.
- `financial_analysis.py` runs the RAG-backed financial report workflow.
- `strategist.py` reflects on strategy parameters.
- `prompting.py`, `state.py`, `sector_questions.py` support the agent prompts and analysis state.

### `vnstock/core`

Infrastructure for model calls and low-level runtime helpers.

- `llm.py` is the OpenAI-compatible proxy client and retry/rate-limit layer.
- `mcp_client.py` and `timing.py` support integration and profiling.

### `vnstock/tools`

Utility/tooling layer that wraps core data and calculations into reusable services.

- `market_tool.py` serves price history, technical reports, and sentiment lookups.
- `search_tool.py` queries the news database and summarizes results.
- `quant_tool.py` computes the alpha model.
- `rag_tool.py` reads cached financial report artifacts.
- `backtest/` contains portfolio accounting, benchmark comparison, and the main backtest engine.

### `vnstock/workflows`

Decision workflows built on top of agent outputs.

- `base.py` defines shared agent-output and workflow result structures.
- `traditional_scoring.py` is the baseline debate + CIO workflow.
- `kelly_criterion.py` is the probability/sizing workflow.
- `markowitz_frontier.py` is the mean-variance portfolio workflow.
- `debate/` contains Bull/Bear argumentation, evidence extraction, and transcript generation.

### `vnstock/engine`

Risk policy and guardrails.

- `risk_engine.py` enforces position, drawdown, stop-loss, and sector limits.

### `vnstock/libs/rag_engine`

Financial RAG subsystem.

- `config.py` reads RAG-specific settings.
- `core.py` builds the LightRAG engine and the storage path.
- `ingest.py` ingests OCR text into the RAG store.
- `retrieval.py` plans queries and performs retrieval/reranking.
- `cli.py`, `__main__.py`, `dashboard.py` expose operational entry points.

### `vnstock/servers`

External service adapter layer.

- `financial_server.py` exposes MCP tools for macro news, stock news, technical reports, price history, quant, and financial report analysis.

### `vnstock/lib`

Static browser assets used by UI-related parts of the repo. This folder is not business logic.

## 2. Public entry files, services, agents, jobs, and data access layers

### Public entry files

- `vnstock/jobs/crawler.py` has a `__main__` block for direct market-data crawling.
- `vnstock/jobs/news_processor.py` has a `main()` entry for batch news-to-sentiment processing.
- `vnstock/libs/rag_engine/__main__.py` launches the RAG CLI.
- `vnstock/libs/rag_engine/cli.py` exposes `index`, `ask`, and `eval`.
- `vnstock/servers/financial_server.py` launches the MCP server.
- `vnstock/tools/backtest_engine.py` is a public import wrapper around the backtest engine.

### Services

These are the main reusable service classes/functions:

- `MarketCrawler`
- `DataRepository`
- `SearchToolkit`
- `MarketToolkit`
- `QuantToolkit`
- `FinancialRAGTool`
- `FinancialAgent`
- `FinancialAnalysisAgent`
- `SharedAgentPool`
- `RiskEngine`
- `BenchmarkAnalyzer`
- `run_autogen_debate`
- `run_portfolio_backtest`
- `generate_financial_report`

### Agents

Core agent types:

- `MacroAgent`
- `NewsAgent`
- `TechnicalAgent`
- `QuantAgent`
- `FinancialAgent`
- `FinancialAnalysisAgent`
- `StrategistAgent`

### Jobs

- `MarketCrawler.sync_tickers()` is the main market ingestion job.
- `MarketCrawler.run_daily_update()` is the batch update wrapper.
- `news_processor.process_day()` converts articles into sentiment rows.
- `news_processor.main()` orchestrates date-window processing.
- `libs/rag_engine.ingest.run_ingest()` is the RAG ingestion job.

### Data access layers

Primary data access boundaries:

- `database/models.py` defines the persistent tables and DB engine.
- `database/repo.py` provides CRUD/query helpers over market data, ratios, sentiment, and logs.
- `search_tool.py` reads from the news SQLite database directly.
- `news_processor.py` also reads news SQLite directly for sentiment aggregation.
- `rag_engine/core.py` reads and writes the RAG working directories.

## 3. Internal data flow

### A. Market and ratio ingestion

1. `run.py crawl-vnstock` instantiates `MarketCrawler`.
2. `MarketCrawler` pulls market history and financial ratios from the external `vnstock` package using subprocess-based isolation.
3. The crawler normalizes columns and writes data through `DataRepository`.
4. `DataRepository` stores rows in `data/vnstock.db` and updates symbol metadata and ratios.

This is the foundation for all later analysis.

### B. News ingestion and sentiment

1. `run.py crawl-news` delegates to `tracking_news`.
2. `news_processor.py` reads articles from the news DB.
3. It clusters similar articles, summarizes them through the shared LLM proxy, and stores daily sentiment rows with `DataRepository.upsert_daily_sentiment()`.
4. Later quantitative and macro analysis reads that sentiment back through `DataRepository.get_decayed_sentiment()`.

### C. Agent analysis

1. `SharedAgentPool.run_all()` runs macro, news, technical, quant, and financial agents in parallel.
2. `MacroAgent` and `NewsAgent` query the news database through `SearchToolkit`.
3. `TechnicalAgent` reads price history through `MarketToolkit`.
4. `QuantAgent` computes alpha using `QuantToolkit`, which itself reads price history, sentiment, and financial ratios from `DataRepository`.
5. `FinancialAgent` resolves a cached financial report, or triggers report generation from `financial_analysis.py`.
6. Each agent sends its narrative to `core.llm.call_llm()`, which is the LLM proxy adapter.

### D. Financial RAG workflow

1. `libs/rag_engine.ingest.run_ingest()` reads OCR text files.
2. It parses `ticker-year-quarter` from filenames and creates a `LightRAG` working directory under `WORKDIR/<ticker>/<year>/<quarter>`.
3. `financial_analysis.py` queries that RAG store with sector-specific questions.
4. The results are converted into a Markdown report and written to `vnstock/analysis_reports/`.
5. `FinancialAgent` and `rag_tool.py` reuse those cached reports later.

### E. Debate and CIO decision layer

1. `workflows/debate/run_autogen_debate()` combines agent outputs into a Bull/Bear debate transcript.
2. `traditional_scoring.py`, `kelly_criterion.py`, and `markowitz_frontier.py` turn that debate plus portfolio context into a CIO decision.
3. `RiskEngine` checks the resulting action against portfolio limits.
4. `Portfolio` executes buy/sell logic, tracks cash, lots, and settlement constraints.

### F. Backtest and persistence

1. `run.py backtest` and `backtest-cognitive` call into `tools/backtest/engine.py`.
2. The engine loads historical prices from `DataRepository`, runs the selected workflows, and steps day-by-day through the portfolio.
3. It writes ledgers, normalized workflow artifacts, equity curves, summaries, timing data, and metrics under `backtest_results/`.
4. `BenchmarkAnalyzer` compares strategy curves against benchmark curves.

### G. UI and external access

1. `servers/financial_server.py` exposes selected tools over MCP for external clients.
2. The RAG CLI and dashboard expose the same corpus in command-line and visual forms.
3. `FinancialAnalysisAgent` and `FinancialRAGTool` let other subsystems consume cached report text without duplicating retrieval logic.

## 4. How this folder connects to `run.py` and `config.py`

### Connection to `run.py`

`run.py` is the orchestration layer. It imports the vnstock subsystems directly:

- `init_db` from `database/models.py`
- `MarketCrawler` from `jobs/crawler.py`
- `generate_financial_report` from `agents/financial_analysis.py`
- `run_ingest` from `libs/rag_engine/ingest.py`
- `query_func` from `libs/rag_engine/retrieval.py`
- `run_portfolio_backtest` and `select_workflows` from `tools/backtest/engine.py`
- `CognitiveBacktestRunner` from `cognitive_trading`

So `vnstock/` provides almost all of the executable domain logic that `run.py` dispatches into.

### Connection to `config.py`

`config.py` is the runtime backbone for the whole folder:

- `database/models.py` uses `paths.vnstock_db_path`.
- `repo.py` stores and reads from the config-driven SQLite location.
- `jobs/crawler.py` and `jobs/news_processor.py` both depend on configured database paths.
- `agents/financial_analysis.py` uses `paths.analysis_reports_dir` and `paths.rag_storage_dir`.
- `core/llm.py` reads model/proxy settings.
- `tools/backtest/portfolio.py` and `workflows/*` read trading and strategy parameters.
- `engine/risk_engine.py` reads risk limits.
- `libs/rag_engine/config.py` reads its own RAG-specific env values, but those still mirror the same overall configuration model.

In practice, `config.py` determines where data lives, which models are called, and what policy limits the workflows obey.

## 5. Core business logic vs adapters/utilities

### Core business logic

These files implement the actual domain behavior:

- `database/models.py`
- `database/repo.py`
- `jobs/crawler.py`
- `jobs/news_processor.py`
- `agents/financial_analysis.py`
- `agents/financial_agent.py`
- `agents/macro_agent.py`
- `agents/news_agent.py`
- `agents/technical_agent.py`
- `agents/quant_agent.py`
- `agents/strategist.py`
- `tools/quant_tool.py`
- `tools/backtest/portfolio.py`
- `tools/backtest/engine.py`
- `workflows/base.py`
- `workflows/traditional_scoring.py`
- `workflows/kelly_criterion.py`
- `workflows/markowitz_frontier.py`
- `workflows/debate/*`
- `engine/risk_engine.py`
- `libs/rag_engine/core.py`
- `libs/rag_engine/ingest.py`
- `libs/rag_engine/retrieval.py`

### Adapters and utilities

These mostly adapt external services or expose helper surfaces:

- `core/llm.py`
- `core/mcp_client.py`
- `core/timing.py`
- `tools/market_tool.py`
- `tools/search_tool.py`
- `tools/rag_tool.py`
- `servers/financial_server.py`
- `libs/rag_engine/cli.py`
- `libs/rag_engine/__main__.py`
- `libs/rag_engine/config.py`
- `tools/backtest_engine.py`
- `lib/*` static assets

The split is not absolute, but this is the useful boundary for reading the code.

## 6. Files to read next, in exact order

1. `vnstock/database/models.py`
2. `vnstock/database/repo.py`
3. `vnstock/core/llm.py`
4. `vnstock/jobs/crawler.py`
5. `vnstock/jobs/news_processor.py`
6. `vnstock/tools/market_tool.py`
7. `vnstock/tools/search_tool.py`
8. `vnstock/tools/quant_tool.py`
9. `vnstock/tools/rag_tool.py`
10. `vnstock/agents/financial_agent.py`
11. `vnstock/agents/financial_analysis.py`
12. `vnstock/agents/macro_agent.py`
13. `vnstock/agents/news_agent.py`
14. `vnstock/agents/technical_agent.py`
15. `vnstock/agents/quant_agent.py`
16. `vnstock/agents/strategist.py`
17. `vnstock/workflows/base.py`
18. `vnstock/workflows/debate/autogen_debate.py`
19. `vnstock/workflows/traditional_scoring.py`
20. `vnstock/workflows/kelly_criterion.py`
21. `vnstock/workflows/markowitz_frontier.py`
22. `vnstock/engine/risk_engine.py`
23. `vnstock/tools/backtest/portfolio.py`
24. `vnstock/tools/backtest/benchmark.py`
25. `vnstock/tools/backtest/engine.py`
26. `vnstock/libs/rag_engine/config.py`
27. `vnstock/libs/rag_engine/core.py`
28. `vnstock/libs/rag_engine/ingest.py`
29. `vnstock/libs/rag_engine/retrieval.py`
30. `vnstock/servers/financial_server.py`

If you want the shortest possible path, start with `database/models.py`, `database/repo.py`, `jobs/crawler.py`, `tools/backtest/engine.py`, and `libs/rag_engine/core.py`.
