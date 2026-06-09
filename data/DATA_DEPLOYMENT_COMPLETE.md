# Data Pipeline — Hướng Dẫn Hoàn Chỉnh

> **Phạm vi:** Tách `data/` thành Docker riêng, bổ sung indicators, deploy lên AWS + Supabase qua Web UI.

---

## Mục lục

1. [Kiến trúc Docker sau khi tách](#1-kiến-trúc-docker-sau-khi-tách)
2. [Cấu trúc requirements — phân tách hoàn toàn](#2-cấu-trúc-requirements--phân-tách-hoàn-toàn)
3. [Cấu trúc .env — phân tách hoàn toàn](#3-cấu-trúc-env--phân-tách-hoàn-toàn)
4. [Code cần bổ sung](#4-code-cần-bổ-sung)
5. [Indicators — thêm như thế nào cho hợp lý](#5-indicators--thêm-như-thế-nào-cho-hợp-lý)
6. [Chuỗi việc cần làm theo thứ tự](#6-chuỗi-việc-cần-làm-theo-thứ-tự)
7. [Supabase — hướng dẫn Web UI](#7-supabase--hướng-dẫn-web-ui)
8. [AWS — hướng dẫn Web UI hoàn toàn](#8-aws--hướng-dẫn-web-ui-hoàn-toàn)

---

## 1. Kiến trúc Docker sau khi tách

### Tổng quan 4 images

```
project-root/
├── Dockerfile.data          ← MỚI: data jobs (ingest + feature build)
├── Dockerfile.ml            ← MỚI: clustering pipeline
├── app/backend/
│   └── Dockerfile           ← đã có: FastAPI API service
└── dashboard/
    └── Dockerfile           ← đã có: Next.js frontend
```

### Dockerfile.data

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps cho lxml, trafilatura, psycopg2
RUN apt-get update && apt-get install -y \
    gcc g++ libxml2-dev libxslt1-dev libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps trước để cache layer
COPY requirements/data.txt requirements/data.txt
RUN pip install --no-cache-dir -r requirements/data.txt

# Chỉ copy những gì data/ cần — KHÔNG copy ml/, vnstock/, app/, dashboard/
COPY config.py config.py
COPY data/ data/

# Không có CMD mặc định
# Mỗi ECS task override CMD riêng
```

### Dockerfile.ml

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ml.txt requirements/ml.txt
RUN pip install --no-cache-dir -r requirements/ml.txt

# ML pipeline cần đọc data từ DB (qua data/storage/)
# nhưng KHÔNG cần data/news/, data/market/fetcher.py
COPY config.py config.py
COPY data/storage/ data/storage/
COPY data/features/ data/features/
COPY data/market/repository.py data/market/repository.py
COPY data/market/calendar.py data/market/calendar.py
COPY data/market/__init__.py data/market/__init__.py
COPY ml/ ml/
```

> **Lý do tách ML ra khỏi data:** ML pipeline (scikit-learn, stumpy, networkx) nặng ~2GB. Data pipeline chỉ cần pandas + sqlalchemy, nhẹ hơn nhiều. Tách giúp build nhanh hơn, lỗi không ảnh hưởng nhau, scale độc lập.

### .dockerignore ở root

```
# Git
.git
.gitignore

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/

# Env files (KHÔNG bao giờ đưa vào image)
.env
.env.*
*.env

# Runtime artifacts
data/feature_artifacts/
data/object_store/
*.db
*.jsonl
*.log

# Frontend (không cần trong Python images)
node_modules/
dashboard/.next/
dashboard/node_modules/

# Docs
docs/
*.md

# IDE
.vscode/
.idea/
```

---

## 2. Cấu trúc requirements — phân tách hoàn toàn

```
requirements/
├── data.txt       ← MỚI: cho Dockerfile.data
├── ml.txt         ← MỚI: cho Dockerfile.ml
├── worker.txt     ← cũ, giữ lại nếu muốn (có thể là data.txt + ml.txt gộp)
└── (backend dùng app/backend/requirements.txt riêng)
```

### `requirements/data.txt`

```txt
# ── Core data processing ────────────────────────────────
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0

# ── Database ────────────────────────────────────────────
sqlalchemy>=2.0
psycopg2-binary>=2.9        # PostgreSQL driver cho Supabase

# ── Technical indicators ────────────────────────────────
pandas-ta>=0.3.14b          # RSI, MACD, Bollinger, ATR, EMA...

# ── HTTP / crawling (cho news pipeline) ─────────────────
httpx>=0.27
tenacity>=8.2

# ── HTML parsing (cho news pipeline) ────────────────────
beautifulsoup4>=4.12
lxml>=5.1
trafilatura>=1.12

# ── Date parsing (cho news) ─────────────────────────────
dateparser>=1.2
python-dateutil>=2.9

# ── Hashing (cho news dedup) ────────────────────────────
# hashlib, hmac: stdlib, không cần cài
```

### `requirements/ml.txt`

```txt
# ── Core ────────────────────────────────────────────────
pandas>=2.2
numpy>=1.26
python-dotenv>=1.0

# ── Database (đọc features từ Supabase) ─────────────────
sqlalchemy>=2.0
psycopg2-binary>=2.9

# ── ML / clustering ─────────────────────────────────────
scikit-learn>=1.4
scipy>=1.12

# ── Graph clustering ────────────────────────────────────
networkx>=3.2
python-louvain>=0.16        # Louvain community detection
# leidenalg>=0.10           # Uncomment nếu dùng Leiden algorithm

# ── Time series similarity ───────────────────────────────
stumpy>=1.12                # Matrix Profile / MPdist

# ── GNN (optional, nặng) ────────────────────────────────
# torch>=2.0                # Uncomment khi implement GNN
# torch-geometric>=2.4
```

---

## 3. Cấu trúc .env — phân tách hoàn toàn

### Local Development

Một file `.env` duy nhất ở root, tất cả service local đọc từ đây:

```env
# ════════════════════════════════════════════════════════
# SHARED — tất cả services dùng
# ════════════════════════════════════════════════════════
DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres

# ════════════════════════════════════════════════════════
# DATA PIPELINE — chỉ Dockerfile.data dùng
# ════════════════════════════════════════════════════════
VNSTOCK_DAILY_SOURCE=KBS
VNSTOCK_INTRADAY_SOURCE=VCI
VNSTOCK_API_KEY=

VNSTOCK_MAX_REQUESTS_PER_MINUTE=30
VNSTOCK_REQUEST_SLEEP_SECONDS=1.0
VNSTOCK_MAX_RETRIES=3
VNSTOCK_BACKOFF_SECONDS=10.0
VNSTOCK_INGESTION_ERRORS_PATH=data/ingestion_errors.jsonl

MARKET_PRIORITY_UNIVERSE=vn80
# MARKET_SYMBOLS=VCB,TCB,BID    # override nếu muốn subset

# Indicator precompute settings
INDICATOR_LOOKBACK_DAYS=252     # 1 năm giao dịch

# News pipeline (để sau)
NEWS_DB_PATH=data/news.db
INGEST_DATE_FROM=2025-01-01
INGEST_DATE_TO=2026-12-31
STORE_CONTENT_HTML=0
STORE_RAW_HTML=0

# ════════════════════════════════════════════════════════
# ML PIPELINE — chỉ Dockerfile.ml dùng
# ════════════════════════════════════════════════════════
CLUSTERING_LOOKBACK_DAYS=120
CLUSTERING_FEATURE=log_return
CLUSTERING_MIN_CLUSTER_SIZE=3

# ════════════════════════════════════════════════════════
# BACKEND — chỉ app/backend/ dùng
# ════════════════════════════════════════════════════════
BACKEND_PORT=8000
ALLOWED_ORIGINS=http://localhost:3000
```

### dashboard/.env.local

```env
# Next.js chỉ đọc .env.local trong dashboard/
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Trên AWS Production

**KHÔNG dùng `.env` file.** Thay bằng AWS Secrets Manager. Xem chi tiết tại [Mục 8.3](#83-tạo-secrets-trong-secrets-manager).

---

## 4. Code cần bổ sung

Dưới đây là **spec/docs cho từng file** — bạn dùng để vibe code:

---

### 4.1 `data/market/ingest_daily.py` — Entry point market ingestion job

**Mục đích:** File này là điểm vào duy nhất khi ECS task chạy job ingest market data. Nó orchestrate toàn bộ flow: lấy danh sách symbols → fetch từng symbol → normalize → validate → store vào Supabase → ghi log kết quả.

**Spec:**
```
Module: data.market.ingest_daily
Chạy bằng: python -m data.market.ingest_daily

Flow:
1. load_dotenv() từ root .env
2. Gọi get_priority_symbols() → list[str] (VN80 mặc định)
3. Khởi tạo IngestionRun record (start_run từ ingestion_repo)
4. Với mỗi symbol:
   a. fetch_daily_ohlcv(symbol, start_date=7 ngày trước, end_date=hôm nay)
   b. normalize_daily(raw_df, symbol)
   c. store_daily_rows(normalized_df) → dict với quality_report
   d. Log kết quả, nếu fail → record_error() và continue (không crash toàn job)
5. finish_run() với tổng số rows, symbols_ok, symbols_failed
6. In summary ra stdout (CloudWatch sẽ pick up)

Lưu ý:
- start_date = today - 7 ngày để cover holidays và weekend
- Không crash khi 1 symbol fail, ghi error và tiếp tục
- Rate limiting: dùng RateLimiter từ data/market/rate_limiter.py
- Log đủ để debug: symbol, rows_stored, errors

Imports cần dùng:
  from data.market.fetcher import fetch_daily_ohlcv
  from data.market.normalizer import normalize_daily
  from data.market.store import store_daily_rows
  from data.market.universe import get_priority_symbols
  from data.market.rate_limiter import RateLimiter
  from data.storage.ingestion_repo import start_run, finish_run, record_error
```

---

### 4.2 `data/features/build_features.py` — Entry point feature + indicator build job

**Mục đích:** Chạy sau market ingestion. Build toàn bộ feature matrix (log_return, volatility...) VÀ tính technical indicators (RSI, MACD, Bollinger...) cho tất cả symbols. Lưu indicators vào bảng `stock_indicators` trong Supabase.

**Spec:**
```
Module: data.features.build_features
Chạy bằng: python -m data.features.build_features

Flow:
1. load_dotenv()
2. symbols = get_priority_symbols()
3. end_date = date.today(), lookback = INDICATOR_LOOKBACK_DAYS env (default 252)
4. Build feature matrix:
   a. build_market_feature_matrix(symbols, end_date, lookback) → MultiIndex DataFrame
   b. save_market_features(run_id, feature_matrix) → lưu artifact pkl
5. Build và lưu indicators:
   a. Với mỗi symbol, lấy OHLCV từ get_daily_ohlcv()
   b. Gọi compute_indicators(ohlcv_df) → indicator_df
   c. Upsert vào bảng stock_indicators qua save_stock_indicators()
6. Ghi run metadata vào feature_runs table

Lưu ý:
- Tách riêng feature build (cho ML) với indicator build (cho dashboard)
- Indicators tính cho 252 ngày (1 năm) để dashboard có đủ data hiển thị
- Nếu 1 symbol fail indicators, log và tiếp tục

Imports cần dùng:
  from data.features.market_features import build_market_feature_matrix
  from data.features.feature_store import save_market_features
  from data.features.indicators import compute_indicators
  from data.storage.indicator_repo import save_stock_indicators
  from data.market.repository import get_daily_ohlcv
  from data.market.universe import get_priority_symbols
```

---

### 4.3 `data/features/indicators.py` — Pure indicator computation

**Mục đích:** Tính tất cả technical indicators từ OHLCV DataFrame. File này là pure function — nhận vào DataFrame, trả ra DataFrame. Không đọc/ghi database. Dùng `pandas_ta` làm engine tính.

**Spec:**
```
Module: data.features.indicators
Không có side effects — pure computation only

Hàm chính:
  compute_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame
  
  Input:
    ohlcv_df: DataFrame với columns [trade_date, open, high, low, close, volume]
              index là integer, sort by trade_date ascending
  
  Output:
    DataFrame cùng index với ohlcv_df, thêm các cột:
    - rsi_14: RSI period 14
    - ema_20: EMA period 20  
    - ema_50: EMA period 50
    - macd_line: MACD line (12, 26)
    - macd_signal: MACD signal (9)
    - macd_hist: MACD histogram
    - bb_upper: Bollinger Band upper (20, 2)
    - bb_lower: Bollinger Band lower (20, 2)
    - bb_mid: Bollinger Band middle (SMA 20)
    - atr_14: ATR period 14
    - volume_sma_20: volume SMA 20 ngày

Cách tính dùng pandas_ta:
  import pandas_ta as ta
  df.ta.rsi(length=14, append=True)
  df.ta.ema(length=20, append=True)
  ...

Lưu ý:
  - Nếu df có ít hơn 50 rows, một số indicators sẽ NaN ở đầu → bình thường
  - Rename columns về tên chuẩn trước khi return (pandas_ta dùng tên như RSI_14)
  - Không raise exception nếu thiếu data, trả về best-effort

Helper hàm (optional):
  get_latest_indicators(ohlcv_df) -> dict
    → Trả về dict chỉ lấy row cuối cùng (để hiển thị "today's indicators")
```

---

### 4.4 `data/storage/indicator_repo.py` — Repository cho stock indicators

**Mục đích:** CRUD cho bảng `stock_indicators`. Pattern giống `market_repo.py` — upsert từng ngày, đọc theo symbol/date range.

**Spec:**
```
Module: data.storage.indicator_repo
Pattern: giống market_repo.py (upsert + query)

Functions:

1. save_stock_indicators(symbol: str, indicator_df: pd.DataFrame) -> int
   - Upsert rows vào stock_indicators
   - Match by (ticker, trade_date) — nếu đã có thì update
   - Return số rows đã upsert
   - indicator_df có columns: trade_date, rsi_14, ema_20, ema_50,
     macd_line, macd_signal, macd_hist, bb_upper, bb_lower, bb_mid,
     atr_14, volume_sma_20

2. get_stock_indicators(
       symbol: str,
       start_date: date | str | None = None,
       end_date: date | str | None = None
   ) -> pd.DataFrame
   - Query stock_indicators by symbol + date range
   - Return DataFrame sorted by trade_date ascending
   - Return empty DataFrame nếu không có data

3. get_latest_indicators(symbol: str) -> dict | None
   - Lấy row mới nhất cho symbol
   - Return dict hoặc None nếu không có

Session management: dùng SessionLocal() từ models.py, pattern try/finally như market_repo.py
```

---

### 4.5 Bổ sung vào `data/storage/models.py` — Bảng StockIndicator

**Mục đích:** SQLAlchemy model cho bảng `stock_indicators`. Thêm vào cuối `models.py` hiện tại.

**Spec:**
```python
# Thêm vào data/storage/models.py

class StockIndicator(Base):
    __tablename__ = "stock_indicators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(16), ForeignKey("tickers.symbol"), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    
    # Trend
    ema_20 = Column(Float)
    ema_50 = Column(Float)
    
    # Momentum
    rsi_14 = Column(Float)
    macd_line = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    
    # Volatility
    bb_upper = Column(Float)
    bb_lower = Column(Float)
    bb_mid = Column(Float)
    atr_14 = Column(Float)
    
    # Volume
    volume_sma_20 = Column(Float)
    
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "trade_date", name="uq_stock_indicators_ticker_date"),
    )
```

---

## 5. Indicators — thêm như thế nào cho hợp lý

### Vấn đề hiện tại

`vnstock/tools/quant_tool.py` đã tính RSI, MACD, EMA, ATR **on-the-fly** mỗi lần được gọi. Điều này ổn cho backtesting (tính theo `ref_date`) nhưng không ổn cho dashboard (chậm, tính lại mỗi request).

### Giải pháp: hai tầng indicator

```
Tầng 1: Precomputed (data/features/indicators.py → stock_indicators table)
         ├── RSI_14, EMA_20, EMA_50
         ├── MACD line/signal/histogram
         ├── Bollinger Bands (upper/lower/mid)
         ├── ATR_14
         └── Volume SMA_20
         → Build mỗi ngày sau market ingestion
         → Dashboard đọc trực tiếp, không tính lại

Tầng 2: Real-time (app/backend/services/market_service.py)
         ├── % change ngày hôm nay
         ├── So sánh close vs EMA (lấy từ precomputed)
         └── Signal nhanh (dựa trên precomputed values)
         → Tính nhẹ từ 2-3 rows cuối
```

### Luồng data đầy đủ khi có indicator

```
[18:30 ICT] market ingestion job
     │ lưu market_ohlcv_1d
     ▼
[19:30 ICT] feature build job
     ├── build_market_feature_matrix() → lưu artifact pkl (cho ML)
     └── compute_indicators() → lưu stock_indicators table (cho dashboard)
     ▼
[20:00 ICT] clustering job (đọc pkl artifact)
     │ lưu stock_clusters
     ▼
Backend API
     ├── GET /api/stocks/{ticker}
     │   → get_stock_indicators() từ stock_indicators table
     │   → get_daily_ohlcv() từ market_ohlcv_1d
     │
     └── GET /api/clusters
         → get_latest_clusters() từ stock_clusters table
```

### Liên kết với quant_tool.py hiện tại

`quant_tool.py` tính alpha score phức tạp (sentiment + foreign flow + momentum). **Giữ nguyên** file đó cho backtesting/agent logic. Indicators mới trong `data/features/indicators.py` là precomputed simple indicators cho dashboard — không overlap.

---

## 6. Chuỗi việc cần làm theo thứ tự

```
PHASE 1 — Chuẩn bị code (local)
│
├── [1] Tạo requirements/data.txt   (nội dung ở Mục 2)
├── [2] Tạo requirements/ml.txt     (nội dung ở Mục 2)
├── [3] Tạo Dockerfile.data         (nội dung ở Mục 1)
├── [4] Tạo Dockerfile.ml           (nội dung ở Mục 1)
├── [5] Bổ sung StockIndicator vào data/storage/models.py
├── [6] Tạo data/features/indicators.py
├── [7] Tạo data/storage/indicator_repo.py
├── [8] Tạo data/market/ingest_daily.py
├── [9] Tạo data/features/build_features.py
└── [10] Test local: python -m data.market.ingest_daily

PHASE 2 — Supabase
│
├── [11] Tạo project Supabase (Mục 7.1)
├── [12] Lấy DATABASE_URL (Mục 7.2)
├── [13] Chạy schema migration (Mục 7.3)
└── [14] Seed tickers (Mục 7.4)

PHASE 3 — AWS Setup
│
├── [15] Tạo ECR repositories (Mục 8.1)
├── [16] Build + push 2 images (data + ml) (Mục 8.2)
├── [17] Tạo Secrets Manager secret (Mục 8.3)
├── [18] Tạo ECS Cluster (Mục 8.4)
└── [19] Tạo Task Definitions (Mục 8.5)

PHASE 4 — Scheduling + Verify
│
├── [20] Tạo EventBridge schedules (Mục 8.6)
├── [21] Run manual test (Mục 8.7)
└── [22] Verify data trong Supabase (Mục 7.5)
```

---

## 7. Supabase — hướng dẫn Web UI

### 7.1 Tạo project

1. Vào **[supabase.com](https://supabase.com)** → **Sign in** → **New project**
2. Điền:
   - **Name:** `vn-clustering` (hoặc tên bạn muốn)
   - **Database Password:** đặt mật khẩu mạnh, **lưu lại ngay** — không xem lại được
   - **Region:** `Southeast Asia (Singapore)` — gần Vietnam nhất
   - **Pricing plan:** Free tier đủ để test
3. Click **Create new project** → chờ ~2 phút

### 7.2 Lấy DATABASE_URL

1. Trong project vừa tạo → **Settings** (icon bánh răng bên trái) → **Database**
2. Kéo xuống phần **Connection string**
3. Chọn tab **URI**
4. Chọn **Session mode** (port 5432) — dùng cho long-running batch jobs
5. Copy URL, thay `[YOUR-PASSWORD]` bằng mật khẩu bạn đặt ở bước trên:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
   ```
6. Paste vào `.env` local: `DATABASE_URL=<url vừa copy>`

> **Transaction mode (port 6543)** dùng khi deploy backend serverless (ít connection hơn). Batch jobs dùng Session mode.

### 7.3 Tạo schema (chạy từ local một lần)

Sau khi có `DATABASE_URL` trong `.env`:

```bash
# Chạy từ project root
python -c "
from dotenv import load_dotenv
load_dotenv()
from data.storage.models import init_db
init_db()
print('Done')
"
```

**Verify trong Supabase:** Table Editor (icon database bên trái) → bạn sẽ thấy các bảng: `tickers`, `market_ohlcv_1d`, `stock_indicators`, `cluster_runs`, `stock_clusters`, v.v.

### 7.4 Seed dữ liệu tickers

```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from data.market.universe import load_universe
from data.storage.models import SessionLocal, Ticker

session = SessionLocal()
for item in load_universe('vn80'):
    session.merge(Ticker(
        ticker=item['symbol'],
        exchange=item['exchange'],
        sector=item['sector'],
        priority=item['priority'],
        is_active=True
    ))
session.commit()
session.close()
print('Seeded', 'vn80 tickers')
"
```

**Verify:** Supabase → Table Editor → `tickers` → bạn thấy ~79 rows.

### 7.5 Verify data sau khi pipeline chạy

Dùng **SQL Editor** trong Supabase (icon `</>` bên trái):

```sql
-- Kiểm tra dữ liệu market đã vào chưa
SELECT ticker, COUNT(*) as rows, MAX(trade_date) as latest
FROM market_ohlcv_1d
GROUP BY ticker
ORDER BY latest DESC
LIMIT 10;

-- Kiểm tra indicators
SELECT ticker, trade_date, rsi_14, macd_hist, bb_upper, bb_lower
FROM stock_indicators
ORDER BY trade_date DESC
LIMIT 20;

-- Kiểm tra cluster run gần nhất
SELECT run_id, started_at, status, algorithm
FROM cluster_runs
ORDER BY started_at DESC
LIMIT 5;
```

### 7.6 Cấu hình Row Level Security (cho backend đọc)

Để backend có thể đọc data, mở Supabase → **Authentication** → **Policies**, hoặc dùng SQL Editor:

```sql
-- Cho phép read public trên các bảng analytics
-- (điều chỉnh theo auth model của bạn)
ALTER TABLE market_ohlcv_1d ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE cluster_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickers ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_read" ON market_ohlcv_1d FOR SELECT USING (true);
CREATE POLICY "allow_read" ON stock_indicators FOR SELECT USING (true);
CREATE POLICY "allow_read" ON stock_clusters FOR SELECT USING (true);
CREATE POLICY "allow_read" ON cluster_runs FOR SELECT USING (true);
CREATE POLICY "allow_read" ON tickers FOR SELECT USING (true);
```

---

## 8. AWS — hướng dẫn Web UI hoàn toàn

### 8.1 Tạo ECR Repositories

**Đường đến:** AWS Console → search `ECR` → **Elastic Container Registry**

1. Click **Create repository**
2. Tạo repository đầu tiên:
   - **Visibility:** Private
   - **Repository name:** `vn-data-pipeline`
   - Click **Create repository**
3. Tạo repository thứ hai (tương tự):
   - **Repository name:** `vn-ml-pipeline`
4. Sau khi tạo, click vào `vn-data-pipeline` → **View push commands** → bạn sẽ thấy 4 lệnh để build + push (cần CLI, nhưng đây là cách duy nhất push image)

> **Lưu ý:** Phần push image lên ECR bắt buộc phải dùng CLI (AWS CLI + Docker). Đây là bước duy nhất không làm được hoàn toàn trên Web UI. Cài AWS CLI ([docs.aws.amazon.com/cli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)) và Docker Desktop, sau đó chạy lệnh từ **View push commands**.

```bash
# Lệnh từ "View push commands" trong ECR console
aws ecr get-login-password --region ap-southeast-1 | \
  docker login --username AWS --password-stdin \
  <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com

# Build data image
docker build -f Dockerfile.data \
  -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-data-pipeline:latest \
  .
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-data-pipeline:latest

# Build ml image
docker build -f Dockerfile.ml \
  -t <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-ml-pipeline:latest \
  .
docker push <ACCOUNT_ID>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-ml-pipeline:latest
```

### 8.2 Tạo IAM Role cho ECS

**Đường đến:** AWS Console → **IAM** → **Roles** → **Create role**

**Role 1: ECS Task Execution Role**

1. **Trusted entity:** AWS Service → **Elastic Container Service** → **Elastic Container Service Task**
2. **Add permissions:** tìm và check:
   - `AmazonECSTaskExecutionRolePolicy`
3. **Role name:** `vn-ecs-task-execution-role`
4. Create role
5. Sau khi tạo, vào role → **Add permissions** → **Create inline policy**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["secretsmanager:GetSecretValue"],
         "Resource": "arn:aws:secretsmanager:ap-southeast-1:*:secret:/vn-clustering/*"
       }
     ]
   }
   ```
6. Policy name: `vn-secrets-access`

### 8.3 Tạo Secrets trong Secrets Manager

**Đường đến:** AWS Console → search `Secrets Manager` → **Store a new secret**

1. **Secret type:** Other type of secret
2. **Key/value pairs** — thêm từng cặp:
   - Key: `DATABASE_URL` / Value: `postgresql://postgres...` (URL từ Supabase)
   - Key: `VNSTOCK_API_KEY` / Value: `<api key của bạn nếu có>`
   - Key: `MARKET_PRIORITY_UNIVERSE` / Value: `vn80`
3. Click **Next**
4. **Secret name:** `/vn-clustering/prod`
5. Click **Next** → **Next** → **Store**
6. Sau khi tạo, **copy Secret ARN** (dạng `arn:aws:secretsmanager:ap-southeast-1:...`) — cần dùng trong Task Definition

### 8.4 Tạo CloudWatch Log Groups

**Đường đến:** AWS Console → **CloudWatch** → **Log groups** → **Create log group**

Tạo 2 log groups:
- `/ecs/vn-data-pipeline`
- `/ecs/vn-ml-pipeline`

**Retention setting:** 30 days (để tiết kiệm cost).

### 8.5 Tạo ECS Cluster

**Đường đến:** AWS Console → **ECS** → **Clusters** → **Create Cluster**

1. **Cluster name:** `vn-clustering`
2. **Infrastructure:** chọn **AWS Fargate (serverless)** — không cần quản lý EC2
3. **Monitoring:** enable Container Insights nếu muốn (có cost)
4. Click **Create**

### 8.6 Tạo Task Definitions

**Đường đến:** ECS → **Task definitions** → **Create new task definition**

**Task Definition 1: vn-market-ingestion**

1. **Task definition family:** `vn-market-ingestion`
2. **Launch type:** Fargate
3. **OS/Architecture:** Linux/X86_64
4. **CPU:** 0.5 vCPU, **Memory:** 1 GB
5. **Task role:** *(để trống hoặc tạo nếu cần)*
6. **Task execution role:** `vn-ecs-task-execution-role`
7. **Container** section → click **Add container**:
   - **Name:** `market-ingestion`
   - **Image URI:** `<ACCOUNT>.dkr.ecr.ap-southeast-1.amazonaws.com/vn-data-pipeline:latest`
   - **Command:** `python,-m,data.market.ingest_daily`
   - **Environment variables** → **Add from Secrets Manager**:
     - Key: `DATABASE_URL` / Value: ARN của secret + `:DATABASE_URL::`
     - Key: `VNSTOCK_API_KEY` / Value: ARN + `:VNSTOCK_API_KEY::`
     - Key: `MARKET_PRIORITY_UNIVERSE` / Value: ARN + `:MARKET_PRIORITY_UNIVERSE::`
   - **Log configuration:**
     - **Log driver:** awslogs
     - **awslogs-group:** `/ecs/vn-data-pipeline`
     - **awslogs-region:** `ap-southeast-1`
     - **awslogs-stream-prefix:** `market-ingestion`
8. Click **Create**

**Task Definition 2: vn-feature-build**

Tương tự, thay:
- **Family:** `vn-feature-build`
- **CPU:** 1 vCPU, **Memory:** 2 GB (pandas cần RAM)
- **Command:** `python,-m,data.features.build_features`
- **awslogs-stream-prefix:** `feature-build`

**Task Definition 3: vn-clustering** (Dockerfile.ml)

Tương tự, thay:
- **Family:** `vn-clustering`
- **Image URI:** `...vn-ml-pipeline:latest`
- **CPU:** 1 vCPU, **Memory:** 3 GB (ML models nặng hơn)
- **Command:** `python,-m,ml.clustering.pipeline`
- **awslogs-stream-prefix:** `clustering`

### 8.7 Tạo EventBridge Schedules

**Đường đến:** AWS Console → search `EventBridge` → **Scheduler** → **Schedules** → **Create schedule**

> **Quan trọng:** Trước tiên cần tạo IAM Role cho EventBridge. Vào IAM → Roles → Create role → Trusted entity: **Scheduler.amazonaws.com** → add policy `AmazonECSTaskExecutionRolePolicy` → name: `vn-eventbridge-ecs-role`.

**Schedule 1: vn-market-ingestion-daily**

1. **Name:** `vn-market-ingestion-daily`
2. **Schedule pattern:** Recurring schedule → **Cron-based**
3. **Cron expression:** `30 11 ? * MON-FRI *`
   - Đây là 11:30 UTC = 18:30 ICT, thứ 2 đến thứ 6
4. **Flexible time window:** Off
5. Click **Next**
6. **Target:** Amazon ECS → **RunTask**
7. **ECS cluster:** `vn-clustering`
8. **Task definition:** `vn-market-ingestion` (latest)
9. **Launch type:** Fargate
10. **Networking:**
    - **VPC:** chọn default VPC
    - **Subnets:** chọn ít nhất 1 subnet
    - **Security groups:** chọn default (hoặc tạo group cho phép outbound)
    - **Auto-assign public IP:** Enabled
11. **Execution role cho EventBridge:** `vn-eventbridge-ecs-role`
12. Click **Next** → **Next** → **Create schedule**

**Schedule 2: vn-feature-build-daily**
- Cron: `30 12 ? * MON-FRI *` (12:30 UTC = 19:30 ICT)
- Task: `vn-feature-build`

**Schedule 3: vn-clustering-daily**
- Cron: `0 13 ? * MON-FRI *` (13:00 UTC = 20:00 ICT)
- Task: `vn-clustering`

### 8.8 Chạy thử thủ công và verify

**Đường đến:** ECS → **Clusters** → `vn-clustering` → **Tasks** → **Run new task**

1. **Family:** `vn-market-ingestion`
2. **Launch type:** Fargate
3. **VPC và Subnets:** như cấu hình trên
4. **Auto-assign public IP:** Enabled
5. Click **Create**
6. Task sẽ xuất hiện trong danh sách với status `RUNNING` → `STOPPED`
7. Click vào task → **Logs** → xem output

**Xem logs chi tiết:**

CloudWatch → **Log groups** → `/ecs/vn-data-pipeline` → `market-ingestion/...` → xem từng log stream.

**Verify trong Supabase:** Chạy SQL query ở Mục 7.5 để kiểm tra data đã được lưu.

---

## Tóm tắt cấu trúc file cuối cùng

```
project-root/
├── Dockerfile.data              ← MỚI
├── Dockerfile.ml                ← MỚI
├── .dockerignore                ← cập nhật
├── config.py                    ← đã có
├── .env                         ← cập nhật với variables mới
│
├── requirements/
│   ├── data.txt                 ← MỚI
│   ├── ml.txt                   ← MỚI
│   └── worker.txt               ← giữ nguyên hoặc remove
│
├── data/
│   ├── market/
│   │   └── ingest_daily.py      ← MỚI (entry point)
│   ├── features/
│   │   ├── indicators.py        ← MỚI
│   │   └── build_features.py    ← MỚI (entry point)
│   └── storage/
│       ├── models.py            ← cập nhật: thêm StockIndicator class
│       └── indicator_repo.py    ← MỚI
│
└── dashboard/
    └── .env.local               ← MỚI (NEXT_PUBLIC_API_URL)
```
