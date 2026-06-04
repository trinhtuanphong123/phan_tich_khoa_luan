# tracking_news subsystem

`tracking_news` is the standalone news-ingestion and news-serving subsystem for the repository. It crawls Vietnamese news sources, normalizes and deduplicates articles into SQLite, and then exposes that corpus through an MCP server, a Streamlit dashboard, and downstream consumers in `vnstock` and `app/backend`.

## 1. Main entry files

### Crawling / ingestion

- `tracking_news/app/ingest/run_once.py` is the main generic ingest entrypoint. It loads enabled source adapters, starts an ingest run, crawls list pages, fetches article pages, parses them, deduplicates them, and writes the results into SQLite.
- `tracking_news/app/ingest/rebuild_cafef.py` is a CafeF-specific rebuild utility. It resets the CafeF-related tables and reruns a full rebuild pipeline.
- `tracking_news/app/ingest/crawl_cafef_timelinelist_raw.py` is a lower-level CafeF utility that saves raw timeline/list-page payloads for inspection or backfill work.

### Serving

- `tracking_news/app/mcp_server.py` is the public serving entrypoint. It exposes search and retrieval tools over the news database through FastMCP.

### Visualization

- `tracking_news/apps/dashboard_streamlit.py` is the Streamlit dashboard entrypoint. It reads the SQLite database directly and presents article, source, run, and trend views.

## 2. News ingestion architecture

The ingestion path is layered and fairly clean.

### Source fetching

- `tracking_news/app/sources/registry.py` resolves which source adapters are enabled.
- `tracking_news/app/sources/__init__.py` defines the adapter interfaces and shared dataclasses.
- Each source file under `tracking_news/app/sources/` implements source-specific list-page and article parsing.
- `tracking_news/app/extract/http_client.py` builds the shared HTTP client, applies timeout and user-agent settings, and performs retries and rate limiting.

### Parsing

- Source adapters turn list pages into candidate article URLs and metadata.
- Adapters then parse article pages into normalized article fields such as title, published time, summary, section, and body text.
- Some adapters use HTML parsing libraries and fallback extractors such as `trafilatura`-style extraction when site markup is inconsistent.

### Normalization

- `tracking_news/app/extract/normalize.py` standardizes text for matching and presentation.
- `tracking_news/app/extract/datetime_utils.py` standardizes article timestamps into a comparable form.
- `tracking_news/app/tickers/vn30.py` contributes ticker extraction for article tagging.
- `tracking_news/app/fomo/scorer.py` contributes the article scoring signal used by the ingest pipeline.
- `tracking_news/app/dedup/hashers.py` and `tracking_news/app/dedup/service.py` compute and query duplicate fingerprints.

### Storage

- `tracking_news/app/db/init_db.py` creates the SQLite schema.
- `tracking_news/app/db/articles_repo.py` writes the article rows and the article-to-ticker join rows.
- `tracking_news/app/db/crawl_state_repo.py` tracks per-source crawl progress and state.
- `tracking_news/app/db/ingest_runs_repo.py` records run-level and section-level ingest telemetry.
- `tracking_news/app/db/conn.py` provides the SQLite connection helper.

### Downstream access

- `tracking_news/app/mcp_server.py` reads the same database and exposes query tools.
- `tracking_news/apps/dashboard_streamlit.py` reads the same database for visualization.
- `vnstock/tools/search_tool.py` and `vnstock/agents/news_agent.py` consume the news corpus for agentic retrieval.
- `app/backend` can point at a cache copy of the news database for backend-facing workflows.

## 3. Public interfaces exposed by this folder

This folder exposes all four of the expected surfaces.

- CLI-style entrypoints: `run_once.py`, `rebuild_cafef.py`, `crawl_cafef_timelinelist_raw.py`
- MCP server: `app/mcp_server.py`
- Dashboard UI: `apps/dashboard_streamlit.py`
- Reusable library surface: the adapter registry, ingestion pipeline, DB repositories, dedup helpers, and extraction helpers

## 4. Relationship to `data/news.db`, `app/backend`, and analysis agents

### `data/news.db`

- The news subsystem uses SQLite as its primary store.
- The default database path is configured in `tracking_news/app/config.py` and is intended to point at the standalone news corpus, typically `data/news.db`.
- `init_db.py` creates and migrates the schema in that file.

### `app/backend`

- The backend runtime is not the source of truth for crawling, but it can read the news cache and trigger crawl-related workflows.
- In practice, `app/backend` points the news stack at a cache copy under `app/data/` for application use, while `tracking_news` itself remains usable as a standalone news service.

### Analysis agents

- The MCP tools in `tracking_news/app/mcp_server.py` are the primary agent-facing interface.
- `vnstock` agents and tools use the same SQLite corpus for retrieval-augmented news analysis.

## 5. Logic boundaries

### Crawler logic

- `tracking_news/app/ingest/run_once.py`
- `tracking_news/app/ingest/pipeline.py`
- `tracking_news/app/ingest/rebuild_cafef.py`
- `tracking_news/app/ingest/crawl_cafef_timelinelist_raw.py`
- all source adapter files under `tracking_news/app/sources/`

### Storage / repository logic

- `tracking_news/app/db/init_db.py`
- `tracking_news/app/db/conn.py`
- `tracking_news/app/db/articles_repo.py`
- `tracking_news/app/db/crawl_state_repo.py`
- `tracking_news/app/db/ingest_runs_repo.py`

### API / server logic

- `tracking_news/app/mcp_server.py`

### UI / dashboard logic

- `tracking_news/apps/dashboard_streamlit.py`

### Shared business logic

- `tracking_news/app/dedup/`
- `tracking_news/app/extract/`
- `tracking_news/app/summarizer.py`
- `tracking_news/app/tickers/vn30.py`
- `tracking_news/app/fomo/scorer.py`

## 6. External dependencies and rate-limit-sensitive integration points

### External dependencies

- `httpx` for HTTP requests
- `tenacity` for retry behavior
- HTML parsing and extraction libraries used by the source adapters
- `fastmcp` for the MCP server
- `streamlit` and `pandas` for the dashboard
- `vnstock.core.llm.call_llm` for agent-side summarization

### Rate-limit-sensitive integrations

- The news sources themselves are the main rate-limit-sensitive boundary.
- CafeF is especially sensitive and has dedicated tuning knobs for per-article delays and deep-backfill behavior.
- Crawl timing, page caps, stale-page thresholds, and retry behavior are all tuned through `tracking_news/app/config.py`.

## 7. File priority map

### Must-understand

- `tracking_news/app/config.py`
- `tracking_news/app/ingest/run_once.py`
- `tracking_news/app/ingest/pipeline.py`
- `tracking_news/app/db/init_db.py`
- `tracking_news/app/db/articles_repo.py`
- `tracking_news/app/sources/__init__.py`
- `tracking_news/app/sources/registry.py`
- `tracking_news/app/sources/cafef.py`
- `tracking_news/app/mcp_server.py`
- `tracking_news/app/summarizer.py`

### Read later

- `tracking_news/app/db/crawl_state_repo.py`
- `tracking_news/app/db/ingest_runs_repo.py`
- `tracking_news/app/dedup/hashers.py`
- `tracking_news/app/dedup/service.py`
- `tracking_news/app/extract/http_client.py`
- `tracking_news/app/extract/datetime_utils.py`
- `tracking_news/app/extract/normalize.py`
- `tracking_news/app/tickers/vn30.py`
- `tracking_news/apps/dashboard_streamlit.py`
- `tracking_news/app/ingest/rebuild_cafef.py`
- `tracking_news/app/ingest/crawl_cafef_timelinelist_raw.py`
- the non-CafeF source adapters such as `vnexpress.py`, `dantri.py`, `tuoitre.py`, `vietnamnet.py`, `nld.py`, `baodautu.py`, and `baochinhphu.py`

### Low priority

- `tracking_news/.mcp.json`
- `tracking_news/vn_news_mcp.egg-info/`
- `tracking_news/app/__init__.py`

## 8. Exact next-file reading order

1. `tracking_news/app/config.py`
2. `tracking_news/app/ingest/run_once.py`
3. `tracking_news/app/ingest/pipeline.py`
4. `tracking_news/app/db/init_db.py`
5. `tracking_news/app/db/articles_repo.py`
6. `tracking_news/app/sources/__init__.py`
7. `tracking_news/app/sources/registry.py`
8. `tracking_news/app/sources/cafef.py`
9. `tracking_news/app/mcp_server.py`
10. `tracking_news/apps/dashboard_streamlit.py`
11. `tracking_news/app/summarizer.py`
12. `tracking_news/app/db/ingest_runs_repo.py`
13. `tracking_news/app/db/crawl_state_repo.py`
14. `tracking_news/app/dedup/service.py`
15. `tracking_news/app/extract/http_client.py`
16. `tracking_news/app/extract/datetime_utils.py`
17. `tracking_news/app/extract/normalize.py`
18. `tracking_news/app/tickers/vn30.py`
19. `tracking_news/app/ingest/rebuild_cafef.py`
20. `tracking_news/app/ingest/crawl_cafef_timelinelist_raw.py`

