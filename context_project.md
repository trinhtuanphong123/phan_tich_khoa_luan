Dưới đây là **bản context cuối đã được verify và chỉnh lại** theo các ý kiến bạn đưa. Bản này thay thế bản context trước đó, tập trung vào dự án hiện tại và các quyết định đã chốt.

---

# Final Project Context: Vietnamese Stock Co-movement Clustering System

## 1. Project direction

The project is being refactored from a broader Vietnamese trading-agent style repository into a focused system for **Vietnamese stock co-movement discovery and clustering**.

The goal is to collect Vietnamese stock market data, process it into clean numerical features, detect groups of stocks that move similarly, store the results, and visualize them through a dashboard.

The system should help answer:

```text
Which Vietnamese stocks move similarly?
Which stocks belong to the same behavioral cluster?
How stable are these clusters over time?
Which stocks recently changed clusters?
What price behavior or news context may explain a cluster movement?
```

The project is **not** an automatic trading bot. It does not directly make buy/sell decisions, does not execute trades, and does not keep the old “agent committee” or “CIO decision” style workflow as part of the new core system.

The core direction is:

```text
market data
→ data ingestion
→ data validation
→ feature engineering
→ clustering
→ cluster storage
→ backend API
→ dashboard visualization
```

## 2. What is in scope

The core project scope includes:

```text
Vietnamese stock market data ingestion
historical data backfill
near-real-time intraday ingestion
5-minute OHLCV bars
daily OHLCV data
data validation and quality checks
technical indicators and market features
stock similarity computation
graph/community-based clustering
cluster run persistence
cluster history per ticker
dashboard visualization
backend API for market and clustering results
```

The first MVP should focus on a simple, stable baseline:

```text
clean market data
→ precomputed indicators and features
→ correlation similarity
→ graph construction
→ community detection
→ cluster labels
→ dashboard/API
```

Advanced methods may be added later:

```text
MPdist
Matrix Profile / motif discovery
foundation model embeddings
GNN embeddings
consensus clustering
news-enriched features
RAG-based explanations
```

## 3. What is out of scope for the MVP

The MVP does not include:

```text
automatic trading execution
buy/sell recommendation
agent committee decision-making
CIO workflow
portfolio optimization as a core objective
financial report OCR as a required pipeline
heavy ML computation inside API request handlers
RAG as a dependency of clustering MVP
```

Old trading-agent, portfolio, backtesting, and agent-debate logic may remain in the repository if useful later, but they should not be connected to the new core pipeline.

## 4. High-level architecture

The project is organized around these layers:

```text
data/
  data ingestion, validation, storage access, feature engineering

ml/
  clustering pipeline, similarity, graph, motifs, validation

app/backend/
  FastAPI API layer

dashboard/
  Next.js dashboard

vnstock/
  reusable legacy utilities and optional RAG/search modules

docs/
  project documentation
```

Expected flow:

```text
vnstock API / market source
→ data/market
→ data/storage
→ Supabase PostgreSQL
→ data/features
→ ml/clustering
→ cluster tables
→ app/backend
→ dashboard
```

Optional later flow:

```text
data/news
→ news storage
→ news features / summaries / embeddings
→ dashboard explanation
→ optional RAG explanation
```

## 5. Core design rule for `data/`

In this project, `data/` is **source code for the data layer**. It is **not** a local runtime data folder.

This means:

```text
data/market      = market data ingestion and validation code
data/features    = feature and indicator building code
data/storage     = database/repository/storage code
data/news        = optional news ingestion code
```

Runtime data should live in deployed services, mainly:

```text
Supabase PostgreSQL
optional Supabase Storage
optional local/EFS storage for news SQLite if the old news pipeline is kept
```

The repository should not rely on local `.db`, `.csv`, `.parquet`, or `.npy` files as production storage.

## 6. Data layer structure

The intended `data/` structure is:

```text
data/
  features/
    feature_store.py
    market_features.py
    indicators.py
    news_features.py          optional later
    __init__.py

  market/
    calendar.py
    universe.py
    rate_limiter.py
    fetcher.py
    normalizer.py
    repository.py
    schemas.py
    store.py
    validator.py
    ingest_daily.py
    quality/
      checks.py
      reports.py
      __init__.py
    __init__.py

  news/
    db/
    dedup/
    extract/
    fomo/
    ingest/
    sources/
    tickers/
    config.py
    fetcher.py
    normalizer.py
    repository.py
    store.py
    summarizer.py
    validator.py
    __init__.py

  storage/
    db.py
    models.py
    base_repo.py
    market_repo.py
    indicator_repo.py
    news_repo.py
    cluster_repo.py
    ingestion_repo.py
    object_store.py
    __init__.py
```

Important clarification: `data/` contains Python code. It does not store the real deployed dataset.

## 7. Market ingestion design

The market data pipeline must support two modes.

### Historical backfill

Historical backfill is used to collect enough past data for features and clustering.

Properties:

```text
runs once or rarely
uses chunking
supports resume
should not repeatedly fetch the same large history
writes clean data into Supabase PostgreSQL
```

### Near-real-time intraday ingestion

Near-real-time ingestion runs during the Vietnamese trading day.

Target use case:

```text
80 tickers
5-minute interval bars
community vnstock API key
near-real-time update
avoid usage limit
```

Vietnam trading session assumption:

```text
Morning:   09:00 → 11:30
Lunch:     11:30 → 13:00
Afternoon: 13:00 → 14:45
```

The ingestion job should not blindly fetch data outside trading sessions.

Example:

```text
At 13:05:
  only fetch closed 5-minute bars that belong to the valid trading session.
  A raw lookback window like 12:50 → 13:05 should be clipped to 13:00 → 13:05.

At 12:30:
  skip because it is lunch break.

At 15:10:
  near-real-time ingestion is no longer needed.
  EOD reconciliation can run instead.
```

## 8. Rate limit strategy for vnstock community account

The system must avoid hitting the usage limit of the vnstock community account.

The design should include:

```text
missing-bar detection
watermarks
symbol sharding
rate limiter
request sleep
retry with exponential backoff
ingestion logs
EOD reconciliation
priority universe
```

For 80 tickers and 5-minute bars:

```text
Morning session: 150 minutes ≈ 30 bars
Afternoon session: 105 minutes ≈ 21 bars
Total: about 51 bars per ticker per day
80 tickers → about 4,080 bars/day
```

The data volume is manageable, but API request count can be high if each ticker is fetched separately.

The initial near-real-time schedule should be conservative:

```text
Start with every 15 minutes.
Use lookback window, for example 15 or 20 minutes.
Only fetch missing bars.
Upsert into database.
After confirming quota safety, consider reducing to every 5 minutes.
```

Environment variables should control request behavior:

```text
VNSTOCK_API_KEY
VNSTOCK_MAX_REQUESTS_PER_MINUTE
VNSTOCK_REQUEST_SLEEP_SECONDS
VNSTOCK_MAX_RETRIES
VNSTOCK_BACKOFF_SECONDS
MARKET_SHARD_SIZE
MARKET_LOOKBACK_MINUTES
MARKET_DELAY_MINUTES
```

## 9. Data files and responsibilities

### `data/market/calendar.py`

Responsible for Vietnamese trading calendar logic:

```text
is_trading_day
is_trading_time
get_current_session
get_closed_bar_time
get_fetch_window
clip_window_to_trading_sessions
```

### `data/market/universe.py`

Responsible for ticker universe management:

```text
load VN80 or selected universe
load active tickers
assign priority
split symbols into shards
```

### `data/market/rate_limiter.py`

Responsible for request throttling and backoff:

```text
sleep between requests
control requests per minute
retry temporary failures
backoff on rate-limit or timeout
```

### `data/market/fetcher.py`

Responsible for calling vnstock API/library.

It should only fetch raw data. It should not normalize, validate, or store.

### `data/market/normalizer.py`

Responsible for converting raw vnstock output into internal schema:

```text
symbol
timestamp
trade_date
open
high
low
close
volume
value
source
fetched_at
```

### `data/market/validator.py`

Responsible for validating market bars:

```text
non-null symbol and timestamp
non-negative OHLCV
high >= open/close/low
low <= open/close/high
no duplicate symbol + timestamp
timestamp inside trading session
no lunch-break bars
valid expected bar count
```

### `data/market/store.py`

Responsible for storing validated market rows through the repository layer.

It should call:

```text
data.storage.market_repo.upsert_ohlcv_5m
data.storage.market_repo.upsert_ohlcv_1d
```

### `data/market/repository.py`

Domain-level market data reader.

It can wrap `data/storage/market_repo.py`.

### `data/market/ingest_daily.py`

Module entry point for daily market ingestion.

Preferred execution pattern:

```bash
python -m data.market.ingest_daily
```

This is preferred over putting all commands into root `run.py`.

## 10. Feature and indicator design

The project should include precomputed technical indicators in the data pipeline.

Important correction: indicator building belongs to the **data/features** layer, not the ML pipeline.

Planned file:

```text
data/features/indicators.py
```

This file should compute indicators using `pandas-ta`, such as:

```text
RSI
MACD
Bollinger Bands
EMA
ATR
```

Additional files:

```text
data/storage/indicator_repo.py
StockIndicator table in data/storage/models.py
```

The `pandas-ta` package belongs in:

```text
requirements/data.txt
```

Clarification about old `vnstock/tools/quant_tool.py`:

```text
vnstock/tools/quant_tool.py may already compute indicators on the fly for old backtesting/agent logic.
Do not duplicate that logic blindly.
The new data/features/indicators.py is a separate precomputed indicator layer for dashboard and clustering features.
```

Feature-related modules:

```text
data/features/market_features.py
  builds return/volatility/volume/liquidity features

data/features/indicators.py
  builds precomputed technical indicators

data/features/build_features.py
  module entry point for feature build

data/features/feature_store.py
  writes/reads feature metadata or feature artifacts
```

Preferred execution:

```bash
python -m data.features.build_features
```

## 11. Storage design

The project uses two database/storage systems.

### PostgreSQL/Supabase

Used for the main structured data:

```text
market data
indicators
features
cluster runs
stock cluster labels
ingestion logs
watermarks
quality reports
```

Accessed through SQLAlchemy.

### SQLite for news

The existing news module currently uses a SQLite database, likely `news.db`.

This is separate from the main Supabase/Postgres system.

Important deployment implication:

```text
If the news SQLite pipeline is deployed inside a container on AWS and must persist data, it needs persistent storage.
For ECS/Fargate this likely means EFS mount.
Otherwise the SQLite file disappears when the container exits.
```

The news SQLite pipeline is not a blocker for market data MVP, but it is a blocker for deploying the news pipeline.

## 12. PostgreSQL/Supabase tables

Core Supabase tables should include:

```text
tickers
market_ohlcv_5m
market_ohlcv_1d
stock_indicators
ingestion_runs
ingestion_errors
ingestion_watermarks
market_data_quality_reports
feature_runs
cluster_runs
stock_clusters
```

Important details:

```text
market_ohlcv_5m primary key:
  symbol + ts + source

market_ohlcv_1d primary key:
  symbol + trade_date + source

stock_indicators should store precomputed indicators:
  symbol
  ts or trade_date
  indicator_name
  indicator_value
  interval
  source/config version
```

The storage write pattern should be idempotent upsert.

Running the same job twice should not create duplicate bars or duplicate indicators.

## 13. News module status and blocker

The news module is kept because it may be useful later.

However, current news imports have a known blocker:

```text
data/news/ still has broken imports from old paths like:
data.tracking_news.app.*
```

All imports inside the news module must be fixed before news deployment.

This blocker affects the news pipeline only. It does not block the market data MVP.

News module current role:

```text
optional enrichment
not required by clustering MVP
can later provide news features, ticker context, summaries, or RAG context
```

## 14. RAG module status

RAG should be kept but treated as optional.

RAG may later be useful for:

```text
news retrieval
cluster explanation
stock Q&A
event explanation
dashboard explanation panels
```

But RAG is not part of the MVP clustering pipeline.

Rule:

```text
Do not connect RAG to ml/clustering/pipeline.py in the first version.
Do not make market clustering depend on RAG.
```

## 15. ML layer design

The `ml/` layer is responsible for clustering and model logic.

Planned structure:

```text
ml/
  clustering/
    graph/
      builder.py
      community.py
    metrics/
      clustering.py
      drift.py
      stability.py
    model/
      fm_embed.py
      gnn.py
    motif/
      consensus.py
      motif.py
    similarity/
      correlation.py
      mp_dist.py
    artifacts.py
    config.py
    pipeline.py
    schemas.py
    validate.py
```

Note: the current discussed structure still uses `model/` and `mp_dist.py` in some places. Earlier naming preference was `models/` and `mpdist.py`, but the verified project notes mention the actual/chosen files as:

```text
ml/clustering/model/
ml/clustering/similarity/mp_dist.py
```

The ML image should be separate from the data image.

## 16. Docker structure

Important correction: Docker should be split into **two separate Dockerfiles**:

```text
Dockerfile.data
Dockerfile.ml
```

### `Dockerfile.data`

Purpose:

```text
data ingestion
market pipeline
feature/indicator building
storage writes
Supabase/Postgres upserts
```

Should include:

```text
data/
vnstock/
config.py
possibly root utilities
requirements/data.txt
```

Should not include heavy ML dependencies.

### `Dockerfile.ml`

Purpose:

```text
clustering pipeline
similarity computation
graph/community detection
motif discovery
future MPdist/GNN/foundation model
```

Should include:

```text
ml/
data/storage/
data/features if needed for loading feature matrices
config.py
requirements/ml.txt
```

Reason for separation:

```text
Do not pull ML libraries into the data ingestion image.
Data image should stay lightweight and run frequently.
ML image can be heavier and run less frequently.
```

This replaces the previous simplified idea of a single `Dockerfile.data-worker`.

## 17. Requirements structure

Important correction: requirements should be split as:

```text
requirements/data.txt
requirements/ml.txt
app/backend/requirements.txt
```

### `requirements/data.txt`

For data pipeline:

```text
pandas
sqlalchemy
psycopg2-binary or psycopg
pandas-ta
httpx
requests
tenacity
lxml
pydantic
pydantic-settings
python-dotenv
vnstock package if required
```

`pandas-ta` belongs here because indicators are computed in `data/features/indicators.py`.

### `requirements/ml.txt`

For ML/clustering:

```text
scikit-learn
scipy
networkx
python-louvain or equivalent
stumpy
numpy
pandas
pyarrow
```

Later, if needed:

```text
torch
torch-geometric
transformers
foundation model dependencies
```

### `app/backend/requirements.txt`

For FastAPI backend only:

```text
fastapi
uvicorn
pydantic
sqlalchemy/client libs if backend reads database directly
```

The backend should not install heavy ML packages.

## 18. Entry point pattern

Important correction: the preferred entry point pattern is:

```bash
python -m <module>
```

rather than:

```bash
python run.py <command>
```

The root `run.py` exists and may remain, but Docker commands should preferably use module entry points.

Planned entry points:

```bash
python -m data.market.ingest_daily
python -m data.features.build_features
```

For ML:

```bash
python -m ml.clustering.pipeline
```

This pattern is cleaner for Docker CMD and avoids a huge root command dispatcher.

## 19. Root `config.py`

The root `config.py` already exists.

This is important because it resolves the previous blocker:

```text
from config import paths
```

The project can use the existing root `config.py` for shared paths/settings. It should be extended carefully for:

```text
database settings
Supabase settings
vnstock settings
market session settings
Docker/runtime settings
```

## 20. Docker runtime model

The data and ML parts are not long-running HTTP services.

They are scheduled containers:

```text
Dockerfile.data
  runs data jobs, exits

Dockerfile.ml
  runs clustering jobs, exits
```

They do not open ports.

They do not need volumes for market data if using Supabase/Postgres.

The news SQLite pipeline is the exception. If deployed and persistent, it may need EFS.

Expected commands:

```bash
python -m data.market.ingest_daily
python -m data.features.build_features
python -m ml.clustering.pipeline
```

## 21. AWS deployment model

The preferred AWS deployment for workers is:

```text
ECR
  stores Docker images:
    stock-data
    stock-ml

ECS Fargate Task
  runs Dockerfile.data or Dockerfile.ml image as one-off tasks

EventBridge Scheduler
  triggers tasks on schedule

Secrets Manager
  stores secrets

CloudWatch
  stores logs
```

AWS components:

```text
ECR repository for data image
ECR repository for ML image
ECS Fargate task definition for data
ECS Fargate task definition for ML
EventBridge Scheduler for market ingestion
EventBridge Scheduler for feature build
EventBridge Scheduler for clustering
Secrets Manager for DATABASE_URL, VNSTOCK_API_KEY, Supabase credentials
CloudWatch for logs
```

The user prefers AWS setup through the web console, not AWS CLI.

However, pushing Docker images to ECR still requires either:

```text
AWS CLI locally
or GitHub Actions / CI
```

This is mostly unavoidable. The AWS web console can create ECR/ECS/EventBridge/Secrets resources, but image build/push needs CLI or CI.

## 22. Supabase deployment model

Supabase will be configured through the web UI.

Supabase responsibilities:

```text
PostgreSQL for market data, indicators, features, clusters
optional Storage for artifacts
not used for news SQLite unless news is migrated later
```

Supabase setup via web:

```text
create project
get DATABASE_URL
create SQL tables using SQL Editor
create Storage bucket only if needed
store service key if Storage/API access is required
```

Important correction:

```text
For MVP, do not use S3.
Use Supabase PostgreSQL.
object_store.py can remain, but should point to local/Supabase Storage or stay inactive.
```

Object storage is not required for MVP unless large artifacts need persistence.

## 23. Deployment storage decision

Earlier context mentioned S3 for artifacts. The verified decision is:

```text
No S3 for MVP.
Use Supabase PostgreSQL as the primary storage.
object_store.py remains as an abstraction, but it should point to local/Supabase Storage or remain unused in MVP.
```

If artifacts become large later, options include:

```text
Supabase Storage
S3
GCS
```

But not for the first MVP.

## 24. Backend and dashboard

Backend:

```text
app/backend/
  routers/
    market.py
    cluster.py or clusters.py
  services/
    market_service.py
    cluster_service.py
```

Dashboard:

```text
dashboard/
  cluster page
  stocks dynamic page
  trading-view
  cluster components
  stock profile
```

Dynamic stock page explanation:

```text
dashboard/src/app/stocks/[ticker]/page.tsx
```

This is one dynamic route file. It handles all tickers:

```text
/stocks/FPT
/stocks/VCB
/stocks/HPG
```

No separate file per ticker is needed.

## 25. API and dashboard route naming

There was a general preference for plural resource names:

```text
clusters
cluster-runs
stocks
```

But some current tree versions use:

```text
cluster
cluster-run
```

This should be standardized during implementation. Preferred final naming:

```text
dashboard/src/app/clusters/page.tsx
dashboard/src/app/api/clusters/route.ts
dashboard/src/app/api/cluster-runs/route.ts
app/backend/routers/clusters.py
```

If current code uses singular names, it should be cleaned consistently later.

## 26. Implementation order, corrected

The implementation order should now reflect the `python -m module` pattern and split Docker images.

Suggested order:

```text
1. Finalize docs and architecture context.

2. Build data/storage:
   db.py
   models.py
   market_repo.py
   indicator_repo.py
   ingestion_repo.py
   cluster_repo.py

3. Build data/market:
   calendar.py
   universe.py
   rate_limiter.py
   fetcher.py
   normalizer.py
   validator.py
   store.py
   repository.py
   ingest_daily.py

4. Build data/features:
   market_features.py
   indicators.py
   build_features.py
   feature_store.py

5. Create Supabase schema:
   market tables
   indicator table
   ingestion tables
   cluster tables

6. Create requirements/data.txt.

7. Create Dockerfile.data.

8. Test:
   python -m data.market.ingest_daily
   python -m data.features.build_features

9. Create requirements/ml.txt.

10. Create Dockerfile.ml.

11. Build baseline ML:
   correlation
   graph
   community detection
   validation
   persistence

12. Test:
   python -m ml.clustering.pipeline

13. Deploy data image to AWS:
   ECR
   ECS Fargate task
   EventBridge schedule
   Secrets Manager
   CloudWatch logs

14. Deploy ML image similarly after data pipeline works.

15. Add backend cluster API.

16. Add dashboard cluster/stock pages.

17. Fix news import paths before deploying news.

18. Integrate news/RAG later as optional enrichment.
```

## 27. Known blockers and risks

Current known blockers:

```text
data/news imports are broken from old data.tracking_news.app.* paths.
News pipeline cannot be deployed until imports are fixed.

News uses SQLite, not Supabase/Postgres.
If deployed on AWS container and persistence is needed, EFS mount is required.

RAG is optional and should not be wired into MVP.

Docker image push to ECR cannot be done purely through AWS web UI.
It needs AWS CLI locally or GitHub Actions/CI.

S3 is not part of MVP.
Do not design MVP around S3 artifact storage.
```

## 28. Current final mental model

The project should be understood as:

```text
A cloud-deployed Vietnamese stock analytics system.

data pipeline:
  collects market data
  builds indicators/features
  writes Supabase PostgreSQL

ml pipeline:
  reads clean data/features
  runs clustering
  writes cluster outputs

backend:
  serves stored results

dashboard:
  visualizes clusters and stock profiles

news/RAG:
  retained for future enrichment
  not MVP dependency
```

The final runtime shape is:

```text
EventBridge Scheduler
  → ECS Fargate Task using Dockerfile.data
  → vnstock API
  → Supabase PostgreSQL

EventBridge Scheduler
  → ECS Fargate Task using Dockerfile.ml
  → Supabase PostgreSQL
  → cluster results

FastAPI backend
  → reads Supabase PostgreSQL

Next.js dashboard
  → calls backend API
```

The project should not be treated as:

```text
a local-only script
a trading bot
a portfolio optimizer
a real-time model server
an LLM agent system
```

This is the corrected final context for the project.
