# System Architecture

## 1. High-level architecture

The project is organized into five main layers:

1. Data Layer
2. ML / Clustering Layer
3. Backend API Layer
4. Dashboard Layer
5. Optional Enrichment Layer

The core system flow is:

Market Data → Data Processing → Feature Building → Clustering → Storage → API → Dashboard

## 2. Data Layer

Located mainly under:

- `data/market/`
- `data/news/`
- `data/features/`
- `data/storage/`

The data layer is source code, not local runtime data storage.

Runtime data is expected to be stored in external managed services such as:

- PostgreSQL / Supabase / Cloud SQL
- Object storage such as Supabase Storage, Google Cloud Storage, or S3

### `data/market/`

Responsible for numerical market data:

- fetch market data
- normalize schema
- validate missing or duplicated records
- store data into cloud database
- expose repository methods for ML and API layers

### `data/news/`

Responsible for news ingestion:

- crawl news articles
- extract metadata
- deduplicate articles
- map articles to tickers
- normalize text fields
- store article data

News is an optional enrichment module.  
It is not required for the first version of the clustering pipeline.

### `data/features/`

Responsible for converting raw data into model-ready features:

- market return features
- volatility features
- liquidity features
- rolling-window features
- optional news count / sentiment / embedding features

### `data/storage/`

Responsible for database and object storage abstraction:

- database connection
- market repository
- news repository
- cluster repository
- artifact storage

## 3. ML / Clustering Layer

Located under:

- `ml/clustering/`

This layer performs:

- preprocessing
- similarity computation
- graph construction
- community detection
- motif discovery
- cluster validation
- artifact writing

The first version should use a simple and stable baseline:

Market Features → Correlation Similarity → kNN Graph → Community Detection → Cluster Metrics

Advanced modules such as MPdist, GNN, foundation model embeddings, and motif discovery can be added later.

## 4. Backend API Layer

Located under:

- `app/backend/`

The backend exposes read-oriented APIs for the dashboard.

Main routers:

- `market.py`
- `clusters.py`

The backend should not run heavy ML computation during HTTP requests.  
It should read precomputed results from the database or storage.

## 5. Dashboard Layer

Located under:

- `dashboard/`

The dashboard visualizes:

- cluster overview
- cluster table
- cluster graph
- stock profile
- price chart
- cluster history
- optional news context

Important routes:

- `/clusters`
- `/stocks/[ticker]`
- `/trading-view`

## 6. Optional RAG / MCP Layer

RAG and MCP modules are kept as optional future extensions.

They are not part of the core clustering flow.

Possible future uses:

- retrieve news context
- explain stock cluster changes
- support question-answering over market and news data
- generate cluster-level textual explanations

## 7. Deployment view

The expected deployment style is daily batch analytics:

1. market data job
2. optional news ingestion job
3. feature building job
4. clustering job
5. API service
6. dashboard web service