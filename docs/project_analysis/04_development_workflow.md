# Development Workflow

## 1. Development principle

The project should be developed incrementally.

Do not build the most advanced ML modules first.  
The first goal is an end-to-end working baseline:

Market data → features → correlation graph → clustering → API → dashboard

## 2. Recommended implementation order

### Phase 1: Clean structure

- keep backend market API
- add cluster API
- keep dashboard as the main frontend
- keep news and RAG as optional modules
- do not connect RAG to clustering yet

### Phase 2: Data layer

Implement or verify:

- `data/storage/db.py`
- `data/storage/market_repo.py`
- `data/storage/cluster_repo.py`
- `data/market/repository.py`
- `data/features/market_features.py`

The data layer must provide a clean feature matrix for ML.

### Phase 3: Baseline clustering

Implement:

- `ml/clustering/config.py`
- `ml/clustering/schemas.py`
- `ml/clustering/similarity/correlation.py`
- `ml/clustering/graph/builder.py`
- `ml/clustering/graph/community.py`
- `ml/clustering/metrics/clustering.py`
- `ml/clustering/pipeline.py`

The first pipeline should use correlation-based graph clustering.

### Phase 4: Persistence

Implement:

- cluster run table
- stock cluster table
- cluster metrics table or JSON field
- artifact writing if needed

Expected outputs:

- run id
- run date
- method
- tickers
- cluster labels
- metrics

### Phase 5: Backend API

Implement:

- `GET /api/clusters`
- `GET /api/cluster-runs`
- `GET /api/stocks/{ticker}`
- `GET /api/stocks/{ticker}/cluster-history`

The API should only read precomputed results.

### Phase 6: Dashboard

Implement:

- `/clusters`
- `/stocks/[ticker]`
- cluster table
- cluster map
- stock profile
- cluster history

### Phase 7: Advanced modules

Only after the baseline works, add:

- MPdist
- motif discovery
- foundation model embedding
- GNN
- news features
- RAG-based explanation

## 3. Coding rules

- Keep data ingestion in `data/`.
- Keep ML logic in `ml/`.
- Keep API logic in `app/backend/`.
- Keep UI logic in `dashboard/`.
- Do not run heavy ML computation inside API request handlers.
- Do not connect optional RAG into the clustering pipeline yet.
- Do not implement trading decision logic.
- Do not implement buy/sell recommendations.
- Do not implement portfolio optimization in the first version.

## 4. Naming conventions

Use plural names for API resources:

- `clusters`
- `cluster-runs`
- `stocks`

Prefer:

- `clusters.py` over `cluster.py`
- `mpdist.py` over `mp_dist.py`
- `models/` over `model/`
- `quality/` over `quality_data/`
- `news-data.ts` over `news_data.ts`

## 5. Testing strategy

Start with small test data:

- 10 to 30 tickers
- 60 to 90 trading days
- correlation-based clustering only

Check:

- feature matrix shape
- missing values
- similarity matrix validity
- graph edge count
- number of clusters
- cluster labels saved correctly
- dashboard reads the latest result

## 6. Definition of done for MVP

The MVP is done when:

- market data can be loaded
- feature matrix can be created
- clustering can run end-to-end
- results are stored
- backend can return latest clusters
- dashboard can show `/clusters`
- stock page `/stocks/[ticker]` can show cluster membership and price chart