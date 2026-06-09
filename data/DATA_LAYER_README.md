# Data Layer — Architecture, Audit & Deployment Guide

> **Scope:** `data/` directory only — market ingestion, news crawling, feature building, and storage.  
> **Target deployment:** AWS (ECS + EventBridge + S3) × Supabase (PostgreSQL)

---

## Table of Contents

1. [What This Layer Does](#1-what-this-layer-does)
2. [Module Map](#2-module-map)
3. [Data Flow (End-to-End)](#3-data-flow-end-to-end)
4. [Database Architecture](#4-database-architecture)
5. [Code Audit — What Is Complete vs. Incomplete](#5-code-audit--what-is-complete-vs-incomplete)
6. [Critical Issue — Broken Import Paths in `data/news/`](#6-critical-issue--broken-import-paths-in-datanews)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [Supabase Setup](#8-supabase-setup)
9. [AWS Deployment Guide](#9-aws-deployment-guide)
10. [Deployment Architecture Diagram](#10-deployment-architecture-diagram)
11. [Job Scheduling (EventBridge)](#11-job-scheduling-eventbridge)
12. [What Must Be Built Before Deployment](#12-what-must-be-built-before-deployment)
13. [Recommended Deployment Order](#13-recommended-deployment-order)

---

## 1. What This Layer Does

The `data/` directory is **source code, not runtime data storage**. It handles:

| Responsibility | Module | Status |
|---|---|---|
| Fetch daily OHLCV from vnstock (KBS/VCI) | `data/market/fetcher.py` | ✅ Complete |
| Normalize market records to a canonical schema | `data/market/normalizer.py` | ✅ Complete |
| Validate OHLC logic, duplicates, session rules | `data/market/validator.py` | ✅ Complete |
| Store clean market data to PostgreSQL | `data/market/store.py` | ✅ Complete |
| Read market data for downstream ML | `data/market/repository.py` | ✅ Complete |
| VN trading calendar / session checks | `data/market/calendar.py` | ✅ Complete |
| Rate limiting for vnstock API calls | `data/market/rate_limiter.py` | ✅ Complete |
| Data quality reporting per symbol | `data/market/quality/` | ✅ Complete |
| VN30 / VN50 / VN80 universe definitions | `data/market/universe.py` | ✅ Complete |
| Build log-return, volatility, liquidity features | `data/features/market_features.py` | ✅ Complete |
| Slice feature matrix for clustering input | `data/features/cluster_features.py` | ✅ Complete |
| Save/load feature artifacts to disk | `data/features/feature_store.py` | ✅ Complete |
| Crawl news from CafeF, VnExpress, DanTri, etc. | `data/news/ingest/` | ✅ Complete (import bug) |
| Deduplicate articles (SHA256 + SimHash) | `data/news/dedup/` | ✅ Complete (import bug) |
| FOMO sentiment scoring | `data/news/fomo/scorer.py` | ✅ Complete (import bug) |
| SQLAlchemy ORM models for all tables | `data/storage/models.py` | ✅ Complete |
| PostgreSQL upsert for market OHLCV | `data/storage/market_repo.py` | ✅ Complete |
| Cluster run + stock cluster persistence | `data/storage/cluster_repo.py` | ✅ Complete |
| Ingestion run tracking + watermarks | `data/storage/ingestion_repo.py` | ✅ Complete |
| SQLite schema for news articles | `data/storage/db/init_db.py` | ✅ Complete |
| Build news-based features for ML | `data/features/news_features.py` | ❌ Empty stub |
| news/fetcher, normalizer, store, validator | `data/news/*.py` (5 files) | ❌ Empty stubs |

---

## 2. Module Map

```
data/
├── market/
│   ├── fetcher.py          # Subprocess-based vnstock calls (KBS daily, VCI intraday)
│   ├── normalizer.py       # Canonical schema: symbol, ts, trade_date, OHLCV, source
│   ├── validator.py        # OHLC logic, duplicates, session rules, quality report
│   ├── store.py            # validate → upsert to PostgreSQL
│   ├── repository.py       # Read interface for ML pipeline (delegates to market_repo)
│   ├── calendar.py         # VN trading day / session / bar time utilities
│   ├── rate_limiter.py     # Request throttling + retry backoff for vnstock
│   ├── schemas.py          # Frozen dataclasses: MarketBar1d, MarketBar5m, etc.
│   ├── universe.py         # VN30 / VN50 / VN80 symbol lists + custom watchlist
│   └── quality/
│       ├── checks.py       # Low-level checks: missing bars, duplicates, out-of-session
│       └── reports.py      # Per-symbol quality report aggregation
│
├── features/
│   ├── market_features.py  # MultiIndex feature matrix: close, log_return, rolling_*, volume_change, liquidity
│   ├── cluster_features.py # Slice feature matrix → clustering input, correlation similarity
│   ├── feature_store.py    # Pickle + JSON metadata artifacts under data/feature_artifacts/
│   └── schemas.py          # FeatureBuildRequest, FeatureMatrix, FeatureArtifact
│
├── news/
│   ├── config.py           # All news env vars (DB path, crawl settings, date window)
│   ├── dedup/              # SHA256 exact match + SimHash near-duplicate detection
│   ├── extract/            # HTTP client (httpx + tenacity), date parser, text normalizer
│   ├── fomo/               # Vietnamese keyword FOMO score (-1.0 to +1.0)
│   ├── ingest/             # Full crawl pipeline: RunOncePipeline + CafeFRebuildPipeline
│   ├── sources/            # 8 site adapters + registry (CafeF, VnExpress, DanTri, ...)
│   ├── tickers/            # VN30 ticker extractor from article text
│   └── summarizer.py       # LLM summarization via vnstock.core.llm (optional)
│
└── storage/
    ├── models.py           # SQLAlchemy ORM: all tables (market, clustering, features, sentiment)
    ├── market_repo.py      # upsert_ohlcv_1d, upsert_ohlcv_5m, get_ohlcv_*, find_missing_bars
    ├── cluster_repo.py     # create_cluster_run, save_stock_clusters, get_latest_clusters
    ├── ingestion_repo.py   # start_run, finish_run, watermark tracking
    ├── news_repo.py        # Article upsert + lookup by ticker/date (PostgreSQL-backed)
    ├── object_store.py     # Local filesystem artifact store (maps to S3 in production)
    ├── base.py             # BaseRepository + DataRepository (legacy ORM helper)
    ├── db.py               # Engine + session factory from DATABASE_URL
    └── db/                 # SQLite-based news database (separate from PostgreSQL)
        ├── init_db.py      # DDL + migrations for news.db
        ├── conn.py         # sqlite3.connect() factory
        ├── articles_repo.py
        ├── crawl_state_repo.py
        ├── ingest_runs_repo.py
        └── migrate_article_tickers.py
```

---

## 3. Data Flow (End-to-End)

### 3.1 Market Data Flow

```
vnstock API (KBS/VCI)
    │
    ▼
data/market/fetcher.py
    │  subprocess isolation (avoids import conflicts with project Python path)
    ▼
data/market/normalizer.py
    │  canonical: symbol, ts, trade_date, open, high, low, close, volume, value, source
    ▼
data/market/validator.py
    │  checks: OHLC logic, negative values, duplicates, session rules
    ▼
data/market/store.py
    │  valid rows → upsert_ohlcv_1d() / upsert_ohlcv_5m()
    ▼
data/storage/market_repo.py
    │
    ▼
Supabase PostgreSQL
    Tables: market_ohlcv_1d, market_ohlcv_5m
```

### 3.2 Feature Building Flow

```
Supabase PostgreSQL (market_ohlcv_1d)
    │
    ▼
data/market/repository.py  →  get_daily_ohlcv()
    │
    ▼
data/features/market_features.py
    │  builds MultiIndex DataFrame:
    │  features × symbols  (close, log_return, rolling_return,
    │                        rolling_volatility, volume_change, liquidity_proxy)
    ▼
data/features/cluster_features.py
    │  slices a single feature (e.g. log_return) → (dates × symbols) matrix
    ▼
data/features/feature_store.py
    │  saves .pkl + .json metadata to local disk (or S3 via object_store)
    ▼
ML clustering pipeline  (ml/clustering/ — outside data/ scope)
```

### 3.3 News Data Flow

```
Vietnamese news sites (CafeF, VnExpress, DanTri, TuoiTre, NLD, ...)
    │
    ▼
data/news/ingest/pipeline.py  (RunOncePipeline / CafeFRebuildPipeline)
    │  fetch HTML → parse article → extract metadata
    ▼
data/news/dedup/   (SHA256 exact + SimHash near-duplicate)
    ▼
data/news/fomo/scorer.py   (Vietnamese FOMO keyword score)
    ▼
data/news/tickers/vn30.py  (extract VN30 tickers from text)
    ▼
data/storage/db/articles_repo.py
    │
    ▼
news.db  (SQLite — local file)
    Tables: articles, article_tickers, crawl_state, ingest_runs

    ⚠️  News uses SQLite, NOT PostgreSQL/Supabase.
        To deploy on AWS, news.db must be on EFS or migrated to PostgreSQL.
```

### 3.4 Clustering Persistence Flow

```
ML clustering output (cluster labels per symbol)
    │
    ▼
data/storage/cluster_repo.py
    │  create_cluster_run()  →  cluster_runs table
    │  save_stock_clusters() →  stock_clusters table
    ▼
Supabase PostgreSQL
    Tables: cluster_runs, stock_clusters, feature_runs
```

---

## 4. Database Architecture

The project uses **two separate database systems**. This is important to understand before deployment.

### System 1 — PostgreSQL via SQLAlchemy (primary)

**Used for:** market data, clustering results, feature runs, ingestion tracking, sentiments, financial ratios.

**Connection:** `DATABASE_URL` environment variable (Supabase connection string).

**Tables defined in `data/storage/models.py`:**

| Table | Purpose |
|---|---|
| `tickers` | Symbol master (exchange, sector, priority) |
| `market_ohlcv_5m` | Intraday OHLCV bars |
| `market_ohlcv_1d` | Daily OHLCV bars |
| `ingestion_runs` | Job run history |
| `ingestion_errors` | Per-symbol errors |
| `ingestion_watermarks` | Last success timestamp per symbol |
| `market_data_quality_reports` | Quality check results |
| `feature_runs` | Feature build job history |
| `cluster_runs` | Clustering job history |
| `stock_clusters` | Cluster label per symbol per run |
| `financial_ratios` | P/E, P/B, ROE, etc. per quarter |
| `agent_logs` | Optional agent decision logs |
| `daily_sentiment` | Aggregated sentiment per ticker per day |
| `backtest_metrics` | Optional backtest results |

**Schema creation:** `data/storage/models.py` → `Base.metadata.create_all(bind=engine)`

### System 2 — SQLite (news articles)

**Used for:** news articles, crawl state, ingest runs for the news pipeline only.

**Connection:** `NEWS_DB_PATH` environment variable (local file path).

**Schema creation:** `data/storage/db/init_db.py` → `init_db()`

**Tables:**

| Table | Purpose |
|---|---|
| `articles` | Full article text, metadata, FOMO score, SimHash |
| `article_tickers` | Many-to-many: ticker ↔ article |
| `crawl_state` | Last crawl status per source/section |
| `ingest_runs` | News crawl job history |
| `ingest_section_runs` | Per-section crawl stats |
| `cafef_timelinelist_raw` | Raw CafeF timeline list items |
| `articles_fts` | FTS5 full-text search index |

> **Deployment note:** SQLite does not work on stateless containers without a persistent volume. On AWS, you need either EFS (persistent) or migrate news storage to PostgreSQL.

---

## 5. Code Audit — What Is Complete vs. Incomplete

### ✅ Production-Ready (with import fix)

- `data/market/` — entire module is solid
- `data/features/market_features.py` and `cluster_features.py`
- `data/storage/market_repo.py`, `cluster_repo.py`, `ingestion_repo.py`
- `data/storage/models.py` — all ORM models
- `data/news/ingest/` — full crawl pipelines exist
- `data/news/sources/` — 8 source adapters complete
- `data/news/dedup/`, `data/news/fomo/`, `data/news/tickers/`

### ❌ Empty Stubs (must be implemented before deployment)

| File | What It Should Do |
|---|---|
| `data/features/news_features.py` | Aggregate news into ML features: article count per window, avg FOMO score, FOMO signal per ticker |
| `data/news/fetcher.py` | Public-facing entry point to fetch news for a ticker/date range |
| `data/news/normalizer.py` | Canonical news record normalization (redundant with `extract/normalize.py` but needed for consistency) |
| `data/news/repository.py` | Read interface for news: `get_articles_by_ticker()`, `get_recent_articles()` |
| `data/news/store.py` | Write interface for news (currently only SQLite via `db/articles_repo.py`) |
| `data/news/validator.py` | Validate article records before storage |

### ⚠️ Partially Working

- `data/storage/object_store.py` — works as local filesystem store; needs S3 adapter for AWS
- `data/features/feature_store.py` — saves to `data/feature_artifacts/` on disk; needs S3 path in production
- `data/storage/news_repo.py` — wraps PostgreSQL `articles` table but the table DDL is not in `models.py`; only in `db/init_db.py` (SQLite DDL)

---

## 6. Critical Issue — Broken Import Paths in `data/news/`

All files under `data/news/` import from `data.tracking_news.app.*`, which does not exist in this repository. This appears to be a migration artifact from a previous project named `tracking_news`.

**Example (broken):**
```python
# data/news/dedup/hashers.py
from data.tracking_news.app.extract.normalize import normalize_for_matching

# data/news/ingest/pipeline.py
from data.tracking_news.app.db.articles_repo import ArticleRecord, insert_article
from data.tracking_news.app.config import INGEST_DATE_FROM, ...
```

**Actual location of those modules in this project:**
```
data.tracking_news.app.extract.normalize  →  data.news.extract.normalize
data.tracking_news.app.config             →  data.news.config
data.tracking_news.app.db.articles_repo   →  data.storage.db.articles_repo
data.tracking_news.app.db.conn            →  data.storage.db.conn
data.tracking_news.app.db.init_db         →  data.storage.db.init_db
data.tracking_news.app.dedup.hashers      →  data.news.dedup.hashers
data.tracking_news.app.dedup.service      →  data.news.dedup.service
data.tracking_news.app.sources            →  data.news.sources
data.tracking_news.app.sources.cafef      →  data.news.sources.cafef
data.tracking_news.app.sources.registry   →  data.news.sources.registry
data.tracking_news.app.fomo.scorer        →  data.news.fomo.scorer
data.tracking_news.app.tickers.vn30       →  data.news.tickers.vn30
data.tracking_news.app.extract.*          →  data.news.extract.*
data.tracking_news.app.ingest.pipeline    →  data.news.ingest.pipeline
```

**Two ways to fix this:**

**Option A (quick fix):** Add a package alias in your project root or `conftest.py`:
```python
# conftest.py or a compatibility shim
import sys
import data.news as _news_pkg
import data.storage.db as _db_pkg
sys.modules['data.tracking_news'] = type(sys)('data.tracking_news')
sys.modules['data.tracking_news.app'] = _news_pkg
# ... etc
```

**Option B (proper fix):** Do a project-wide find-and-replace. The news module has approximately 15 files that need their imports updated. This is the correct long-term approach.

**Until this is fixed, the entire `data/news/` pipeline will fail with `ModuleNotFoundError` at import time.**

---

## 7. Environment Variables Reference

Create a `.env` file at the project root. All variables below are read at runtime.

### Database

```env
# Supabase / PostgreSQL connection string (required)
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres

# News SQLite path (for local/dev; use EFS mount path on AWS)
NEWS_DB_PATH=/mnt/efs/news.db
```

### vnstock Data Source

```env
# API source (default: KBS for daily, VCI for intraday)
VNSTOCK_DAILY_SOURCE=KBS
VNSTOCK_INTRADAY_SOURCE=VCI
VNSTOCK_API_KEY=your_api_key_if_required

# Rate limiting
VNSTOCK_MAX_REQUESTS_PER_MINUTE=30
VNSTOCK_REQUEST_SLEEP_SECONDS=1.0
VNSTOCK_MAX_RETRIES=3
VNSTOCK_BACKOFF_SECONDS=10.0

# Error log path
VNSTOCK_INGESTION_ERRORS_PATH=data/ingestion_errors.jsonl
```

### Market Universe

```env
# Which universe to use: vn30, vn50, vn80, or custom_watchlist
MARKET_PRIORITY_UNIVERSE=vn80

# Override: comma-separated list of specific symbols
MARKET_SYMBOLS=VCB,TCB,BID,CTG,MBB

# Priority symbols (for ML pipeline)
MARKET_PRIORITY_SYMBOLS=VCB,TCB,FPT,VIC
```

### News Crawling

```env
# Date window for article ingestion
INGEST_DATE_FROM=2025-01-01
INGEST_DATE_TO=2026-06-09

# Crawl settings
MAX_PAGES_PER_SECTION=32
ARTICLE_FETCH_WORKERS=4
CAFEF_ONLY_ARTICLE_FETCH_WORKERS=4
CRAWL_RATE_LIMIT_SECONDS=1.0
CRAWL_TIMEOUT_SECONDS=20

# Storage flags (set to 0 to save disk/DB space)
STORE_CONTENT_HTML=1
STORE_RAW_HTML=0

# CafeF-specific
CAFEF_ONLY_MODE=0
CAFEF_DEEP_BACKFILL_MODE=0
```

### AWS-specific

```env
# S3 bucket for feature artifacts and object store
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=ap-southeast-1

# ECS task role will provide credentials; no key/secret needed if using IAM roles
```

---

## 8. Supabase Setup

### Step 1 — Create a Supabase project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose **AWS ap-southeast-1** (Singapore) for lowest latency to Vietnam
3. Set a strong database password
4. Note your **Project Reference ID**

### Step 2 — Get the connection string

In Supabase dashboard → **Settings** → **Database**:

- Use the **Session mode** pooler URL for long-running jobs:
  ```
  postgresql://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
  ```
- Use the **Transaction mode** pooler for serverless/Lambda:
  ```
  postgresql://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres?pgbouncer=true
  ```

### Step 3 — Initialize the schema

Run this once to create all tables:

```python
# run_migrations.py (project root)
from dotenv import load_dotenv
load_dotenv()
from data.storage.models import init_db
init_db()
print("PostgreSQL schema created.")
```

Or via the Supabase SQL editor, paste the output of:
```python
from sqlalchemy.schema import CreateTable
from data.storage.models import Base, engine
for table in Base.metadata.sorted_tables:
    print(CreateTable(table).compile(engine))
```

### Step 4 — Create the `tickers` table seed data

The `market_ohlcv_1d` and `stock_clusters` tables have a foreign key to `tickers.symbol`. You must insert symbol records before inserting market data:

```python
from data.market.universe import load_universe
from data.storage.models import SessionLocal, Ticker

session = SessionLocal()
for item in load_universe("vn80"):
    t = Ticker(
        ticker=item["symbol"],
        exchange=item["exchange"],
        sector=item["sector"],
        priority=item["priority"],
        is_active=item["is_active"],
    )
    session.merge(t)
session.commit()
session.close()
print("Tickers seeded.")
```

### Step 5 — Enable Row Level Security (optional but recommended)

For the dashboard to read data safely, enable RLS on read-only tables:

```sql
-- In Supabase SQL editor
ALTER TABLE market_ohlcv_1d ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE cluster_runs ENABLE ROW LEVEL SECURITY;

-- Allow all reads (adjust to your auth model as needed)
CREATE POLICY "Allow read" ON market_ohlcv_1d FOR SELECT USING (true);
CREATE POLICY "Allow read" ON stock_clusters FOR SELECT USING (true);
CREATE POLICY "Allow read" ON cluster_runs FOR SELECT USING (true);
```

---

## 9. AWS Deployment Guide

### 9.1 Infrastructure Overview

| Component | AWS Service | Purpose |
|---|---|---|
| Market ingestion job | ECS Fargate (scheduled task) | Daily OHLCV fetch + store |
| News crawl job | ECS Fargate (scheduled task) | Crawl 8 news sources |
| Feature build job | ECS Fargate (scheduled task) | Build feature matrix |
| Clustering job | ECS Fargate (scheduled task) | Run ML clustering |
| News SQLite | EFS (Elastic File System) | Persistent SQLite volume |
| Feature artifacts | S3 | Pickle/JSON artifacts |
| Secrets | AWS Secrets Manager | `DATABASE_URL`, API keys |
| Job scheduling | EventBridge Scheduler | Cron triggers |
| Logs | CloudWatch Logs | Container stdout/stderr |

### 9.2 Docker Image

Create a single `Dockerfile` at the project root that all jobs share:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies for lxml, trafilatura, vnstock
RUN apt-get update && apt-get install -y \
    gcc g++ curl git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run market ingestion
CMD ["python", "-m", "data.market.ingest_daily"]
```

Each ECS task definition overrides the CMD to run a specific job:
- Market job: `python -m data.market.ingest_daily`
- News job: `python -m data.news.ingest.run_once`
- Feature job: `python -m data.features.build_features`
- Cluster job: `python -m ml.clustering.pipeline`

### 9.3 ECR — Push Your Image

```bash
# Authenticate
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com

# Build and push
docker build -t vn-clustering .
docker tag vn-clustering:latest \
  <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-clustering:latest
docker push \
  <account-id>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-clustering:latest
```

### 9.4 EFS — Persistent Volume for News SQLite

If you keep SQLite for news (instead of migrating to PostgreSQL):

```bash
# Create EFS filesystem
aws efs create-file-system \
  --region ap-southeast-1 \
  --tags Key=Name,Value=vn-news-db

# Create mount target in the same VPC/subnet as ECS tasks
aws efs create-mount-target \
  --file-system-id fs-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --security-groups sg-xxxxxxxxx
```

In your ECS task definition, add a volume:
```json
{
  "volumes": [{
    "name": "news-db-efs",
    "efsVolumeConfiguration": {
      "fileSystemId": "fs-xxxxxxxxx",
      "rootDirectory": "/news"
    }
  }],
  "containerDefinitions": [{
    "mountPoints": [{
      "sourceVolume": "news-db-efs",
      "containerPath": "/mnt/efs"
    }]
  }]
}
```

Set `NEWS_DB_PATH=/mnt/efs/news.db` in your task's environment variables.

### 9.5 S3 — Feature Artifacts

The current `data/storage/object_store.py` writes to a local directory. For AWS, adapt it to use S3:

```python
# Suggested wrapper (add to object_store.py)
import boto3, os

def upload_to_s3(local_path: str, s3_key: str) -> str:
    bucket = os.environ["AWS_S3_BUCKET"]
    boto3.client("s3").upload_file(local_path, bucket, s3_key)
    return f"s3://{bucket}/{s3_key}"
```

Feature artifacts flow:
1. `feature_store.py` saves `.pkl` to `/tmp/feature_artifacts/`
2. After save, upload to S3: `s3://your-bucket/feature_artifacts/{run_id}.pkl`
3. Record S3 path in `feature_runs.artifact_path` column

### 9.6 Secrets Manager

Store sensitive values in AWS Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name /vn-clustering/prod \
  --secret-string '{
    "DATABASE_URL": "postgresql://...",
    "VNSTOCK_API_KEY": "...",
    "NEWS_DB_PATH": "/mnt/efs/news.db"
  }'
```

In ECS task definition, reference secrets:
```json
{
  "secrets": [
    {
      "name": "DATABASE_URL",
      "valueFrom": "arn:aws:secretsmanager:ap-southeast-1:<account>:secret:/vn-clustering/prod:DATABASE_URL::"
    }
  ]
}
```

### 9.7 IAM Role for ECS Tasks

Create a task execution role with these policies:
- `AmazonECSTaskExecutionRolePolicy` (pull ECR images, write CloudWatch logs)
- Custom policy for Secrets Manager read
- Custom policy for S3 read/write to your bucket

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": "arn:aws:secretsmanager:ap-southeast-1:<account>:secret:/vn-clustering/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

---

## 10. Deployment Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS (ap-southeast-1)                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    EventBridge Scheduler                 │   │
│  │  Cron: 18:30 ICT   Cron: 19:00 ICT   Cron: 19:30 ICT  │   │
│  └───────┬──────────────────┬────────────────┬─────────────┘   │
│          │                  │                │                  │
│          ▼                  ▼                ▼                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  ECS Task:   │  │  ECS Task:   │  │  ECS Task:   │         │
│  │   Market     │  │    News      │  │   Feature    │         │
│  │  Ingestion   │  │   Crawl      │  │    Build     │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                 │                  │                  │
│         │          ┌──────▼──────┐           │                  │
│         │          │     EFS     │           │                  │
│         │          │  news.db    │           │                  │
│         │          │  (SQLite)   │           │                  │
│         │          └─────────────┘           │                  │
│         │                                    │                  │
│         ▼                                    ▼                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                    Supabase (PostgreSQL)              │       │
│  │  market_ohlcv_1d   cluster_runs   stock_clusters     │       │
│  │  feature_runs      ingestion_runs  tickers           │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│         │                                    │                  │
│         ▼                                    ▼                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                         S3                           │       │
│  │  feature_artifacts/{run_id}.pkl                      │       │
│  │  object_store/{path}                                 │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  ┌─────────────────────┐   ┌──────────────────────────────┐    │
│  │   ECR               │   │   CloudWatch Logs             │    │
│  │   vn-clustering:*   │   │   /ecs/market-ingestion       │    │
│  │   (Docker image)    │   │   /ecs/news-crawl             │    │
│  └─────────────────────┘   └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                    │ reads
                    ▼
          ┌────────────────────┐
          │  FastAPI Backend   │
          │  (app/backend/)    │
          └────────────────────┘
                    │
                    ▼
          ┌────────────────────┐
          │  Next.js Dashboard │
          │  (dashboard/)      │
          └────────────────────┘
```

---

## 11. Job Scheduling (EventBridge)

Vietnamese market closes at 15:00 ICT. Suggested schedule:

| Job | Cron (UTC) | ICT Time | Description |
|---|---|---|---|
| Market Ingestion | `30 11 * * 1-5` | 18:30 | Fetch daily OHLCV after market close |
| News Crawl | `00 12 * * 1-5` | 19:00 | Crawl 8 news sources |
| Feature Build | `30 12 * * 1-5` | 19:30 | Build feature matrix from fresh market data |
| Clustering | `00 13 * * 1-5` | 20:00 | Run clustering pipeline |

Create an EventBridge schedule via AWS Console or CLI:

```bash
aws scheduler create-schedule \
  --name market-ingestion-daily \
  --schedule-expression "cron(30 11 ? * MON-FRI *)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{
    "Arn": "arn:aws:ecs:ap-southeast-1:<account>:cluster/vn-clustering",
    "RoleArn": "arn:aws:iam::<account>:role/EventBridgeECSRole",
    "EcsParameters": {
      "TaskDefinitionArn": "arn:aws:ecs:...:task-definition/market-ingestion:1",
      "LaunchType": "FARGATE",
      "NetworkConfiguration": {
        "AwsvpcConfiguration": {
          "Subnets": ["subnet-xxx"],
          "SecurityGroups": ["sg-xxx"],
          "AssignPublicIp": "ENABLED"
        }
      }
    }
  }'
```

---

## 12. What Must Be Built Before Deployment

These are blockers. The project cannot run end-to-end without them.

### Blocker 1 — Fix news import paths

All ~15 files in `data/news/` must have `data.tracking_news.app.*` replaced with the correct module paths. See Section 6 for the full mapping.

### Blocker 2 — Create entry-point scripts

The ECS tasks need runnable Python modules. These do not exist yet:

```
# Needed (create these):
data/market/ingest_daily.py     # fetch → normalize → validate → store for all universe symbols
data/features/build_features.py # load market data → build features → save artifact
```

Example for `ingest_daily.py`:
```python
"""Entry point for the daily market ingestion ECS task."""
from dotenv import load_dotenv
load_dotenv()

from datetime import date, timedelta
from data.market.fetcher import fetch_daily_ohlcv
from data.market.normalizer import normalize_daily
from data.market.store import store_daily_rows
from data.market.universe import get_priority_symbols

def main():
    symbols = get_priority_symbols()
    end_date = date.today()
    start_date = end_date - timedelta(days=5)  # buffer for gaps
    
    for symbol in symbols:
        raw = fetch_daily_ohlcv(symbol, start_date, end_date)
        normalized = normalize_daily(raw, symbol)
        result = store_daily_rows(normalized)
        print(f"{symbol}: stored {result['quality_report']['stored_row_count']} rows")

if __name__ == "__main__":
    main()
```

### Blocker 3 — `config/paths.py` must exist

`data/storage/models.py` imports `from config import paths`. This module must exist at project root:

```python
# config/paths.py
from pathlib import Path

project_dir = Path(__file__).resolve().parents[1]
data_dir = project_dir / "data"
vnstock_db_path = data_dir / "vnstock.db"
```

### Blocker 4 — News SQLite on stateless containers

SQLite does not work on ECS without EFS. Either:
- Mount an EFS volume and set `NEWS_DB_PATH=/mnt/efs/news.db`, OR
- Migrate the news database to PostgreSQL (add `articles` table to `models.py`)

### Improvement — S3 adapter for `object_store.py`

Currently writes to local disk. Add an S3 backend so feature artifacts survive container restarts.

---

## 13. Recommended Deployment Order

Follow this sequence for a clean first deployment:

```
Step 1 ── Fix import paths in data/news/ (all 15 files)

Step 2 ── Ensure config/paths.py exists at project root

Step 3 ── Set up Supabase
           - Create project in AWS ap-southeast-1
           - Run init_db() to create PostgreSQL schema
           - Seed tickers table

Step 4 ── Build and push Docker image to ECR

Step 5 ── Create EFS filesystem for news.db
           - Create mount target in your VPC
           - Set NEWS_DB_PATH=/mnt/efs/news.db

Step 6 ── Store secrets in AWS Secrets Manager
           - DATABASE_URL, VNSTOCK_API_KEY, NEWS_DB_PATH

Step 7 ── Create ECS Cluster + Task Definitions
           - One task per job (market, news, features, clustering)
           - Attach EFS volume to news task
           - Inject secrets from Secrets Manager

Step 8 ── Create EventBridge schedules
           - Market: 18:30 ICT weekdays
           - News: 19:00 ICT weekdays
           - Features: 19:30 ICT weekdays
           - Clustering: 20:00 ICT weekdays

Step 9 ── Run market ingestion manually (test)
           - Check CloudWatch logs
           - Verify rows in Supabase market_ohlcv_1d

Step 10 ─ Run feature build manually (test)
           - Verify artifact in S3

Step 11 ─ Enable scheduled runs
           - Monitor first automated run
           - Set CloudWatch alarms on task failure
```

---

*Generated for the Vietnamese stock clustering project — data layer deployment reference.*
*Last reviewed: June 2026*
