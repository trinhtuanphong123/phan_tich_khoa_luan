# Processing Flow

## 1. Core daily flow

The core system is designed as a daily batch pipeline.

The expected flow is:

1. Fetch market data.
2. Normalize and validate data.
3. Store clean market data.
4. Build market features.
5. Run clustering pipeline.
6. Store clustering results.
7. Serve results through backend API.
8. Display results on dashboard.

## 2. Market data flow

Market data flow:

External market source
→ `data/market/fetcher.py`
→ `data/market/normalizer.py`
→ `data/market/validator.py`
→ `data/market/store.py`
→ cloud database

Quality checks should include:

- missing ticker
- missing date
- duplicate records
- non-positive price
- abnormal volume
- stale data
- insufficient lookback window

## 3. Feature building flow

Feature flow:

Clean market data
→ `data/features/market_features.py`
→ feature matrix
→ ML clustering pipeline

For the first version, the feature matrix can be based on:

- close price
- log return
- rolling return
- volatility
- volume-based features

## 4. Clustering flow

Baseline clustering flow:

Feature matrix
→ preprocessing
→ correlation similarity
→ graph construction
→ community detection
→ cluster metrics
→ persistence

Suggested first baseline:

- lookback window: 90 trading days
- input: log return matrix
- similarity: Pearson correlation
- graph: k-nearest-neighbor graph
- clustering: Louvain or Leiden
- output: cluster label per ticker

## 5. Advanced clustering flow

Advanced modules can be added later:

- MPdist for subsequence similarity
- Matrix Profile for motif discovery
- foundation model embeddings
- GNN-based graph embeddings
- consensus clustering

These modules should not be required for the first working version.

## 6. News flow

News flow is optional:

External news source
→ `data/news/ingest/pipeline.py`
→ deduplication
→ normalization
→ ticker mapping
→ storage
→ optional feature extraction

News should be treated as enrichment, not as a hard dependency of the clustering pipeline.

## 7. RAG flow

RAG is an optional future layer.

Possible future flow:

Clean news articles
→ embedding/indexing
→ retrieval
→ cluster explanation
→ dashboard explanation panel

RAG should not be imported by the core clustering pipeline in the first version.

## 8. API flow

Backend API flow:

Dashboard request
→ FastAPI router
→ service layer
→ repository
→ database/storage
→ response JSON

Heavy computation should not happen during API requests.

## 9. Dashboard flow

Dashboard flow:

User opens `/clusters`
→ dashboard requests cluster data
→ backend returns latest clustering result
→ dashboard renders table, map, metrics, and history

User opens `/stocks/FPT`
→ dashboard requests stock profile
→ backend returns price, cluster, history, and optional news
→ dashboard renders stock profile page