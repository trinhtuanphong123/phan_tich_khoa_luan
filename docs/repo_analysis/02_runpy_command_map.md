# `run.py` Command Map

This note analyzes `run.py` only.

## 1. Top-level commands and subcommands

`run.py` is a CLI dispatcher built with `argparse`. It requires one top-level command and, for `rag`, one nested subcommand.

### Top-level commands

- `backtest`
- `backtest-cognitive`
- `sync`
- `prepare` alias for `sync`
- `rag`
- `analyze`
- `crawl-vnstock`
- `crawl-news`

### Nested `rag` subcommands

- `rag index`
- `rag query`
- `rag dashboard`

## 2. What module each command dispatches into

### `crawl-vnstock`

Dispatches to:

- `vnstock.database.models.init_db()`
- `vnstock.jobs.crawler.MarketCrawler.sync_tickers()`

Purpose:

- initializes the database schema
- crawls or refreshes market data into `data/vnstock.db`

### `crawl-news`

Dispatches to:

- `tracking_news.app.ingest.run_once.main()`

Purpose:

- sets crawl-window environment variables
- crawls news into the configured news database

### `sync` / `prepare`

Dispatches to:

- `vnstock.database.models.init_db()`
- `vnstock.jobs.crawler.MarketCrawler.sync_tickers()`
- `tracking_news.app.ingest.run_once.main()`
- `vnstock.agents.financial_analysis.generate_financial_report()`

Purpose:

- one-shot data preparation pipeline
- syncs price data
- syncs news
- caches financial reports

### `analyze`

Dispatches to:

- `vnstock.agents.financial_analysis.generate_financial_report()`
- `vnstock.agents.financial_agent.normalize_financial_quarter()`

Purpose:

- generates a Markdown financial report artifact from OCR/RAG source documents

### `rag index`

Dispatches to:

- `vnstock.libs.rag_engine.ingest.run_ingest()`

Purpose:

- ingests OCR text files into the financial RAG store

### `rag query`

Dispatches to:

- `vnstock.libs.rag_engine.retrieval.query_func()`

Purpose:

- queries the financial RAG store
- prints retrieved context count and answer

### `rag dashboard`

Dispatches to:

- `streamlit run vnstock/libs/rag_engine/dashboard.py`

Purpose:

- launches the RAG UI in Streamlit

### `backtest`

Dispatches to:

- `vnstock.tools.backtest.engine.select_workflows()`
- `vnstock.tools.backtest.engine.run_portfolio_backtest()`

Supporting runtime dependency:

- `vnstock.database.repo.DataRepository`
- `vnstock.jobs.crawler.MarketCrawler` if backtest data is missing

Purpose:

- runs legacy portfolio backtests for Traditional, Kelly, and Markowitz workflows

### `backtest-cognitive`

Dispatches to:

- `cognitive_trading.runner.CognitiveBacktestRunner`

Supporting runtime dependency:

- `vnstock.jobs.crawler.MarketCrawler` if backtest data is missing

Purpose:

- runs the cognitive trading backtest pipeline

## 3. Core workflows vs utilities

### Core workflows

These are the commands that represent the main business pipeline of the repo:

- `crawl-vnstock`
- `crawl-news`
- `sync` / `prepare`
- `analyze`
- `rag index`
- `rag query`
- `backtest`
- `backtest-cognitive`

Why these are core:

- they ingest or prepare domain data
- they create analysis artifacts
- they drive RAG and reporting
- they produce backtest outputs
- they are the data-to-decision path of the system

### Utilities and support commands

- `rag dashboard`

Why it is more of a utility:

- it is a visualization frontend for the RAG subsystem
- it does not produce the core analytical outputs itself
- it depends on data already ingested into the RAG store

## 4. Likely user journey from ingestion to analysis to backtest to UI

The command flow implied by `run.py` is roughly:

### Step 1: Ingest market data

Typical command:

```bash
python run.py crawl-vnstock --tickers FPT,VCB,HPG
```

This initializes the DB and loads OHLCV history into `data/vnstock.db`.

### Step 2: Ingest news

Typical command:

```bash
python run.py crawl-news --news-days 10 --source cafef
```

This loads news into the news database and sets the ingest window for the crawler.

### Step 3: Prepare a synchronized workspace

Typical command:

```bash
python run.py sync --tickers FPT,VCB --year 2025 --quarter Q4 --news-days 3
```

This is the all-in-one preparation command:

- sync market data
- sync news incrementally
- cache financial analysis artifacts

### Step 4: Index report text into RAG

Typical command:

```bash
python run.py rag index --input vnstock/libs/data/financial_reports
```

This makes OCR text searchable by the financial RAG subsystem.

### Step 5: Generate analysis

Typical command:

```bash
python run.py analyze --ticker FPT --year 2025 --quarter Q4
```

This emits a cached Markdown report under `vnstock/analysis_reports/`.

### Step 6: Query the RAG layer

Typical command:

```bash
python run.py rag query --query "What are the key risks for FPT in Q4 2025?" --ticker FPT --year 2025 --quarter Q4 --mode hybrid
```

This retrieves source context and a generated answer.

### Step 7: Run backtests

Typical command:

```bash
python run.py backtest --tickers FPT,HPG,SSI,GAS,VCB --start 2026-03-24 --end 2026-03-25 --workflows Traditional,Kelly,Markowitz
```

This produces backtest artifacts and performance summaries.

### Step 8: Run cognitive backtests

Typical command:

```bash
python run.py backtest-cognitive --tickers VN30 --start 2026-01-05 --end 2026-01-26
```

This exercises the higher-order planner/swarm/debate workflow.

### Step 9: Open the UI surfaces

The CLI does not start the main app UIs directly, but the workflow culminates in two separate frontend surfaces:

- realtime app: `app/frontend` on port `3001`
- research dashboard: `dashboard` on port `8000`

The likely loop is:

- ingest and sync data through `run.py`
- analyze and backtest through `run.py`
- inspect results in the Next.js UI or research dashboard

## Practical summary

`run.py` is the orchestration layer for the repo. Its commands split into:

- ingestion commands
- preparation commands
- analysis and RAG commands
- backtest commands
- a UI launcher for the RAG dashboard

The strongest signal is that the repo is built around a data-first workflow:

1. ingest market/news/report data
2. index and analyze it
3. backtest strategies
4. inspect results in web UIs
