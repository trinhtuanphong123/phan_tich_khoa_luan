# Data Layer Design

## 1. Important convention

In this project, the `data/` directory contains source code for data processing.  
It does not store runtime datasets.

Runtime data should be stored in external services such as:

- PostgreSQL-compatible database
- Supabase
- Cloud SQL
- object storage
- managed blob storage

This convention is important because the project is designed to run on deployed services rather than relying on local files.

## 2. Data layer responsibilities

The data layer is responsible for:

- fetching raw data
- normalizing schema
- validating quality
- storing clean data
- reading clean data for downstream modules
- building model-ready features

The data layer should not perform clustering directly.  
Clustering belongs to the `ml/` layer.

## 3. Market data module

Path:

- `data/market/`

Responsibilities:

- fetch OHLCV data
- fetch benchmark/index data
- normalize ticker symbols and dates
- validate missing trading days
- detect duplicates
- check stale data
- store clean records
- provide repository access for downstream pipelines

Suggested files:

- `fetcher.py`
- `normalizer.py`
- `validator.py`
- `store.py`
- `repository.py`
- `schemas.py`
- `quality/checks.py`
- `quality/reports.py`

## 4. News data module

Path:

- `data/news/`

Responsibilities:

- crawl articles from supported sources
- extract title, body, source, timestamp, URL
- normalize article format
- deduplicate articles
- detect related tickers
- store clean articles
- provide article lookup by ticker/date

News is optional for the first clustering version.  
It should not block market-data clustering if news ingestion fails.

## 5. Feature module

Path:

- `data/features/`

Responsibilities:

- transform raw market data into numerical features
- create rolling return features
- create volatility and liquidity features
- create optional news features
- write feature tables if needed

Example market features:

- log return
- rolling return
- rolling volatility
- volume change
- liquidity proxy

Example news features:

- news count in last 7 days
- news count in last 30 days
- sentiment score
- topic or event signal
- article embedding aggregation

## 6. Storage module

Path:

- `data/storage/`

Responsibilities:

- manage database connections
- define database models
- expose repositories
- store and load clustering results
- upload and download artifacts

Suggested repositories:

- `market_repo.py`
- `news_repo.py`
- `cluster_repo.py`

Suggested storage utilities:

- `db.py`
- `object_store.py`
- `base_repo.py`
- `models.py`

## 7. Data flow

The normal data flow is:

1. `data/market/fetcher.py` fetches market data.
2. `data/market/normalizer.py` normalizes records.
3. `data/market/validator.py` checks quality.
4. `data/market/store.py` writes records to the database.
5. `data/features/market_features.py` builds model-ready features.
6. `ml/clustering/pipeline.py` consumes features and produces clusters.

Optional news flow:

1. `data/news/ingest/pipeline.py` crawls news.
2. `data/news/dedup/` removes duplicates.
3. `data/news/store.py` writes articles.
4. `data/features/news_features.py` builds aggregated news features.
5. ML or dashboard may consume those features later.

## 8. Design rule

Raw ingestion code should stay in `data/`.  
Machine learning logic should stay in `ml/`.  
API serving should stay in `app/backend/`.  
UI logic should stay in `dashboard/`.