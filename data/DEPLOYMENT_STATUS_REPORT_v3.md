# Báo Cáo Trạng Thái Triển Khai — Lần 3
**Ngày:** June 10, 2026 | **So với báo cáo lần 2:** Cập nhật theo code mới nhất

---

## Tóm tắt thay đổi so với báo cáo lần 2

| Hạng mục | Lần 2 | Lần 3 |
|---|---|---|
| `crawler.run_daily_update()` crash | 🔴 Bug | ✅ Đã fix |
| Storage repos tách riêng | 🔴 Chưa có | ✅ Hoàn chỉnh |
| `models.py` naming | ⚠️ Inconsistent | ✅ Chuẩn hóa |
| `market_repo` thêm helpers | ❌ Thiếu | ✅ Có đủ |
| `crawler.repo.close()` trong `market_tool.py` | 🔴 Bug | 🔴 **VẪN CÒN** |
| `data/storage/db/` broken imports | 🔴 5 files | 🔴 **VẪN CÒN** |
| `news_processor.py` tracking_news import | 🔴 Bug | 🔴 **VẪN CÒN** |
| Infrastructure files (Docker, requirements) | ❌ Chưa có | ❌ **VẪN CHƯA** |
| Supabase setup | ❌ Chưa | ❌ **VẪN CHƯA** |
| AWS deployment | ❌ Chưa | ❌ **VẪN CHƯA** |

**Đánh giá tổng thể:** Code nghiệp vụ tiến bộ rõ rệt. Storage layer sạch và đúng kiến trúc. Tuy nhiên market MVP vẫn chưa thể deploy vì chưa có infrastructure files và còn 1 bug runtime chưa fix.

---

## 1. Những gì đã hoàn chỉnh

### 1.1 Storage Layer — Đã đạt mức sản xuất

Refactor này là thay đổi lớn nhất và quan trọng nhất trong lần này:

**`data/storage/` hiện có kiến trúc rõ ràng:**

```
BaseRepository          ← core session + generic helpers
    ├── RatioRepository      ← financial ratios
    ├── SymbolRepository     ← ticker metadata, sector
    ├── SentimentRepository  ← daily_sentiment
    └── AgentLogRepository   ← agent_logs

DataRepository (repo.py) ← kế thừa cả 4 trên, chỉ là compatibility facade
market_repo (module)     ← standalone functions, không phải class
indicator_repo (module)  ← standalone functions, không phải class
ingestion_repo (module)  ← standalone functions, không phải class
cluster_repo (module)    ← standalone functions, không phải class
```

Boundary này đúng và sạch. `market_repo` không phải class vì không cần state — mỗi call tự quản lý session.

### 1.2 ORM Models — Naming chuẩn hóa hoàn toàn

`models.py` hiện tại:

| Model | ORM attribute | DB column | Synonym |
|---|---|---|---|
| `Ticker` | `symbol` | `symbol` | `ticker` |
| `MarketOHLCV5m` | `symbol`, `ts` | `symbol`, `ts` | `ticker`, `timestamp` |
| `MarketOHLCV1d` | `symbol`, `ts` | `symbol`, `ts` | `ticker`, `date` |
| `StockIndicator` | `symbol` | `ticker` | `ticker` |
| `FinancialRatio` | `symbol` | `ticker` | `ticker` |
| `AgentLog` | `symbol` | `ticker` | `ticker` |
| `DailySentiment` | `symbol` | `ticker` | `ticker` |
| `BacktestMetric` | `symbol` | `ticker` | `ticker` |

**Lưu ý quan trọng về DB column naming:** Các model non-market (`StockIndicator`, `FinancialRatio`, v.v.) vẫn dùng `"ticker"` làm tên column trong DB — đây là thiết kế có chủ đích để backward compat với DB schema cũ. ORM attribute là `symbol`, synonym là `ticker`. Khi query qua ORM dùng `Model.symbol` là đúng. Khi viết raw SQL phải dùng `ticker` làm tên column.

### 1.3 Entry Points — Hoàn chỉnh và đúng pattern

Ba ECS task entry points đã sẵn sàng:

**`data/market/ingest_daily.py`**
- Load dotenv từ project root
- Rate limiter với retry/backoff
- Per-symbol error isolation (1 symbol fail không crash toàn job)
- `ingestion_runs` + `ingestion_errors` logging
- Structured stdout logs (CloudWatch-ready)

**`data/market/ingest_intraday.py`**
- Session-aware: skip nếu không phải giờ giao dịch
- Watermark-driven window per symbol
- `clip_window_to_trading_sessions()` để không fetch ngoài session
- Per-symbol `update_watermark()` sau khi store thành công

**`data/features/build_features.py`**
- `FeatureRun` record với status tracking
- Tách biệt feature matrix (cho ML) và indicators (cho dashboard)
- Per-symbol indicator error isolation
- Structured stdout logs

### 1.4 `vnstock/jobs/crawler.py` — Market path sạch

```python
# Trước (báo cáo lần 2):
self.repo = DataRepository()
# market history → self.repo.save_daily_data()
# market delete → self.repo.replace_daily_data() (delete toàn bộ rồi insert)
# check latest → self.repo.db.query(MarketDataDaily)...

# Sau (hiện tại):
self.ratio_repo = RatioRepository()
self.symbol_repo = SymbolRepository()
# market history → market_repo.upsert_ohlcv_1d()
# market delete → market_repo.delete_ohlcv_1d()
# check latest → market_repo.get_latest_bar_time()
# check existing → market_repo.get_existing_trade_dates()
```

`run_daily_update()` finally block đã đúng: `self.ratio_repo.close()` + `self.symbol_repo.close()`.

### 1.5 `vnstock/tools/quant_tool.py` — Hoàn toàn sạch

```python
self.ratio_repo = RatioRepository()
self.sentiment_repo = SentimentRepository()
# market history → market_repo.get_daily_ohlcv()
# ratio → self.ratio_repo.get_latest_ratio()
# sentiment → self.sentiment_repo.get_decayed_sentiment()
```

Không còn phụ thuộc `DataRepository` cho bất kỳ data nào. `close()` gọi đúng cả 2 repos.

---

## 2. Các vấn đề còn tồn tại

### 2.1 🔴 Bug chưa fix — `crawler.repo.close()` trong `market_tool.py`

**File:** `vnstock/tools/market_tool.py`

**Code hiện tại (line ~trong get_price_data):**
```python
crawler = MarketCrawler()
try:
    ...
finally:
    crawler.repo.close()  ← AttributeError: 'MarketCrawler' has no attribute 'repo'
```

`MarketCrawler.__init__` hiện tại:
```python
self.ratio_repo = RatioRepository()
self.symbol_repo = SymbolRepository()
# KHÔNG có self.repo
```

**Hậu quả:** Bất cứ khi nào `get_price_data()` được gọi với symbol không có trong DB (lần đầu chạy), code sẽ fallback sang crawler fetch và crash với `AttributeError` trong finally block. Đây là code path hay gặp trong thực tế.

**Fix 2 dòng:**
```python
# Thay:
finally:
    crawler.repo.close()

# Thành:
finally:
    crawler.ratio_repo.close()
    crawler.symbol_repo.close()
```

### 2.2 🔴 Broken imports trong `data/storage/db/`

**5 files vẫn import từ namespace không tồn tại:**

| File | Import cần fix |
|---|---|
| `articles_repo.py` | `from data.tracking_news.app.dedup.service import find_duplicate` |
| `conn.py` | `from data.tracking_news.app.config import NEWS_DB_PATH` |
| `ingest_runs_repo.py` | `from data.tracking_news.app.sources import SectionDiscoveryStats` |
| `init_db.py` | `from data.tracking_news.app.config import NEWS_DB_PATH` |
| `migrate_article_tickers.py` | `from data.tracking_news.app.db.conn import connect` |

**Tại sao không block market MVP ngay bây giờ:** `data/storage/db/__init__.py` là file rỗng, Python không auto-import các file trong package. `ingest_daily.py` và `build_features.py` không import bất kỳ thứ gì từ `data.storage.db.*`. Nên khi build `Dockerfile.data` và chạy market pipeline, những file này sẽ không được load.

**Tại sao vẫn cần fix:** News pipeline không thể chạy cho đến khi fix. Và bất kỳ developer nào import nhầm sẽ gặp `ModuleNotFoundError` ngay lập tức.

**Fix mapping:**
```python
# conn.py và init_db.py:
# Trước: from data.tracking_news.app.config import NEWS_DB_PATH
import os
NEWS_DB_PATH = os.getenv("NEWS_DB_PATH", "data/news.db")

# articles_repo.py:
# Trước: from data.tracking_news.app.dedup.service import find_duplicate
from data.news.dedup.service import find_duplicate

# ingest_runs_repo.py:
# Trước: from data.tracking_news.app.sources import SectionDiscoveryStats
from data.news.sources import SectionDiscoveryStats

# migrate_article_tickers.py:
# Trước: from data.tracking_news.app.db.conn import connect
from data.storage.db.conn import connect
```

### 2.3 🔴 Broken imports trong `vnstock/jobs/` và `vnstock/tools/`

| File | Import cần fix | Ghi chú |
|---|---|---|
| `news_processor.py` | `from data.tracking_news.app import summarizer as tsummarizer` | Module-level import → crash khi import file |
| `search_tool.py` | `from data.tracking_news.app.summarizer import summarize_for_agent` | Lazy import bên trong method → crash khi gọi method |

`news_processor.py` crash ngay khi import file (module-level). `search_tool.py` chỉ crash khi `_summarize()` được gọi (lazy import), nhưng `SearchToolkit` class itself import được.

Cả hai file này nằm trong `vnstock/` nên **không ảnh hưởng đến `Dockerfile.data`** (Dockerfile.data không copy `vnstock/`). Chỉ ảnh hưởng khi chạy local hoặc trong Dockerfile khác có vnstock.

### 2.4 🟡 `crawler.py` — Key mismatch trong `_ratio_record_from_rows`

**Code hiện tại:**
```python
return {
    "ticker": ticker,   # ← key "ticker"
    "quarter": quarter,
    ...
}
```

**`ratio_repo.save_financial_ratios()` gọi:**
```python
self.upsert(FinancialRatio, {"symbol": ticker, "quarter": quarter}, record)
# payload = {"symbol": ticker, "quarter": quarter, **record}
# record có key "ticker" → payload có cả "symbol" và "ticker"
```

**`FinancialRatio(**payload)`** nhận `ticker=...` không map vào constructor vì `ticker` là `synonym("symbol")` — synonym không được nhận qua constructor `**kwargs`. Kết quả phụ thuộc vào SQLAlchemy version — có thể silently ignore hoặc raise TypeError.

**Fix đơn giản:** Đổi key `"ticker"` thành `"symbol"` trong `_ratio_record_from_rows()`:
```python
return {
    "symbol": ticker,  # ← đổi từ "ticker" thành "symbol"
    "quarter": quarter,
    ...
}
```

### 2.5 🟡 Feature artifacts — Local disk không tồn tại trên ECS

**`feature_store.py`:**
```python
FEATURE_ARTIFACTS_DIR = paths.data_dir / "feature_artifacts"
```

ECS Fargate container là stateless. Sau khi `build_features` job kết thúc, container tắt và `feature_artifacts/` biến mất. `feature_runs.artifact_path` lưu path local → ML pipeline không đọc được.

**Giải pháp tạm thời (đã thảo luận):** ML pipeline (`ml/clustering/pipeline.py`) nên build feature matrix từ DB trực tiếp thay vì đọc artifact file. Đây là cách đúng nhất cho stateless deployment.

**Giải pháp lâu dài:** Upload artifact lên Supabase Storage hoặc S3 và lưu URL vào `feature_runs.artifact_path`.

### 2.6 🟡 `get_priority_symbols()` — Chỉ trả về priority=1

```python
# universe.py
return [
    item["symbol"]
    for item in sorted(...)
    if bool(item["is_active"]) and int(item["priority"]) == 1
]
```

Trong VN80, priority=1 chỉ có ~15 symbols (VN30 có priority 1 và 2, VN80 additional có priority 2 và 3). Nếu muốn ingest đủ 79 symbols VN80, cần override qua env var:

```env
MARKET_SYMBOLS=ACB,BCM,BID,BVH,CTG,FPT,GAS,GVR,HDB,HPG,LPB,MBB,MSN,MWG,PLX,POW,SAB,SHB,SSB,SSI,STB,TCB,TPB,VCB,VHM,VIB,VIC,VJC,VNM,VPB,VRE,ANV,BAF,BMP,...
```

Hoặc sửa hàm để nhận priority threshold thay vì cứng `== 1`.

---

## 3. Trạng thái từng module

### data/ layer

| Module | Hoàn chỉnh | Chạy được | Deploy được | Ghi chú |
|---|---|---|---|---|
| `market/fetcher.py` | ✅ | ✅ | ✅ | Subprocess isolation tốt |
| `market/normalizer.py` | ✅ | ✅ | ✅ | |
| `market/validator.py` | ✅ | ✅ | ✅ | |
| `market/store.py` | ✅ | ✅ | ✅ | |
| `market/repository.py` | ✅ | ✅ | ✅ | Thin wrapper đúng pattern |
| `market/calendar.py` | ✅ | ✅ | ✅ | |
| `market/rate_limiter.py` | ✅ | ✅ | ✅ | |
| `market/universe.py` | ✅ | ✅ | ✅ | priority=1 workaround cần env var |
| `market/ingest_daily.py` | ✅ | ✅ | ✅ | **Entry point sẵn sàng** |
| `market/ingest_intraday.py` | ✅ | ⚠️ | ⚠️ | Cần test runtime với vnstock |
| `features/market_features.py` | ✅ | ✅ | ✅ | |
| `features/indicators.py` | ✅ | ✅ | ✅ | Self-implemented, không cần pandas_ta |
| `features/cluster_features.py` | ✅ | ✅ | ✅ | |
| `features/feature_store.py` | ✅ | ✅ | ⚠️ | Artifacts mất khi ECS stop |
| `features/build_features.py` | ✅ | ✅ | ⚠️ | Phụ thuộc artifact path |
| `features/news_features.py` | ❌ | ❌ | ❌ | Empty stub, không block MVP |
| `storage/models.py` | ✅ | ✅ | ✅ | Schema đầy đủ |
| `storage/market_repo.py` | ✅ | ✅ | ✅ | Canonical write/read |
| `storage/indicator_repo.py` | ✅ | ✅ | ✅ | |
| `storage/ingestion_repo.py` | ✅ | ✅ | ✅ | |
| `storage/cluster_repo.py` | ✅ | ✅ | ✅ | |
| `storage/ratio_repo.py` | ✅ | ⚠️ | ⚠️ | Key mismatch với crawler dict |
| `storage/symbol_repo.py` | ✅ | ✅ | ✅ | |
| `storage/sentiment_repo.py` | ✅ | ✅ | ✅ | |
| `storage/db/conn.py` | ❌ | ❌ | ❌ | Broken import |
| `storage/db/init_db.py` | ❌ | ❌ | ❌ | Broken import |
| `storage/db/articles_repo.py` | ❌ | ❌ | ❌ | Broken import |
| `storage/db/ingest_runs_repo.py` | ❌ | ❌ | ❌ | Broken import |
| `storage/db/migrate_article_tickers.py` | ❌ | ❌ | ❌ | Broken import |

### vnstock/ layer (liên quan đến data pipeline)

| Module | Hoàn chỉnh | Ghi chú |
|---|---|---|
| `jobs/crawler.py` | ✅ | Market path sạch, ratio/symbol đúng |
| `jobs/news_processor.py` | ⚠️ | Import tracking_news còn broken |
| `tools/market_tool.py` | ⚠️ | `crawler.repo.close()` bug còn đó |
| `tools/quant_tool.py` | ✅ | Hoàn toàn sạch |
| `tools/chart_tool.py` | ✅ | Handle ts/date column đúng |
| `tools/search_tool.py` | ⚠️ | Lazy import tracking_news trong method |

---

## 4. Infrastructure — Chưa có gì

Đây là điểm mấu chốt: **toàn bộ infrastructure để deploy vẫn chưa tồn tại**.

| File cần tạo | Nội dung | Độ ưu tiên |
|---|---|---|
| `Dockerfile.data` | Python 3.11-slim + system deps + data.txt deps + COPY config.py + COPY data/ | P0 |
| `Dockerfile.ml` | Python 3.11-slim + ml.txt deps + COPY data/storage + data/features + data/market/repository + ml/ | P0 |
| `requirements/data.txt` | pandas, sqlalchemy, psycopg2-binary, httpx, lxml, trafilatura, dateparser | P0 |
| `requirements/ml.txt` | pandas, sqlalchemy, psycopg2-binary, scikit-learn, scipy, networkx, louvain, stumpy | P0 |
| `.env.example` | Template với tất cả biến môi trường, không có giá trị thật | P1 |
| `.dockerignore` (cập nhật) | Loại bỏ .env, __pycache__, *.db, feature_artifacts | P0 |

---

## 5. Thứ tự công việc để deploy được

### Bước 1 — Fix bugs trước khi build Docker (ưu tiên cao nhất)

```
[1] Fix market_tool.py: crawler.repo.close()
    → Đổi thành crawler.ratio_repo.close() + crawler.symbol_repo.close()
    File: vnstock/tools/market_tool.py
    Vị trí: trong get_price_data(), khối finally của fallback crawler

[2] Fix crawler.py: _ratio_record_from_rows() key "ticker" → "symbol"
    File: vnstock/jobs/crawler.py
    Dòng: return {"ticker": ticker, ...} → return {"symbol": ticker, ...}

[3] Fix data/storage/db/conn.py và init_db.py
    → Thay import tracking_news bằng os.getenv("NEWS_DB_PATH", "data/news.db")
    → Không cần fix ngay cho market MVP nhưng nên làm để code clean

[4] Quyết định về feature artifacts
    → Nếu deploy soon: cho ML pipeline tự build feature matrix từ DB
    → Nếu muốn đúng: implement upload lên Supabase Storage
```

### Bước 2 — Tạo infrastructure files

```
[5] Tạo requirements/data.txt
[6] Tạo requirements/ml.txt
[7] Tạo Dockerfile.data
[8] Tạo Dockerfile.ml
[9] Cập nhật .dockerignore
[10] Tạo .env.example
```

### Bước 3 — Setup Supabase

```
[11] Tạo project Supabase (Singapore region)
[12] Lấy DATABASE_URL → cập nhật .env local
[13] Chạy: python -c "from data.storage.models import init_db; init_db()"
[14] Seed tickers VN80
[15] Verify trong Supabase Table Editor
```

### Bước 4 — Test local trước khi push lên AWS

```
[16] Test ingest_daily local:
     DATABASE_URL=<supabase_url> python -m data.market.ingest_daily
     → Verify rows trong Supabase SQL Editor

[17] Test build_features local:
     DATABASE_URL=<supabase_url> python -m data.features.build_features
     → Verify stock_indicators trong Supabase

[18] Build Docker image local:
     docker build -f Dockerfile.data -t vn-data-test .
     docker run --env-file .env vn-data-test python -m data.market.ingest_daily
```

### Bước 5 — AWS

```
[19] Tạo ECR repositories (vn-data-pipeline, vn-ml-pipeline)
[20] Push images lên ECR
[21] Tạo IAM roles
[22] Tạo Secrets Manager secret (/vn-clustering/prod)
[23] Tạo CloudWatch log groups
[24] Tạo ECS Cluster (Fargate)
[25] Tạo 3 Task Definitions (market-ingestion, feature-build, clustering)
[26] Run manual test task từng task
[27] Verify data trong Supabase
[28] Tạo EventBridge schedules
```

---

## 6. Scorecard tổng thể

```
Code nghiệp vụ (data pipeline logic)
  data/market/*          ████████████ 100%
  data/features/*        ██████████░░  85%  (artifact path chưa xử lý)
  data/storage/repos     ████████████ 100%
  data/storage/models    ████████████ 100%
  data/storage/db/*      ███░░░░░░░░░  25%  (5 files broken imports)
  data/news/*            ████░░░░░░░░  30%  (market MVP không cần)

vnstock/ liên quan
  jobs/crawler.py        █████████░░░  90%  (ratio key mismatch nhỏ)
  tools/market_tool.py   ████████░░░░  80%  (1 bug chưa fix)
  tools/quant_tool.py    ████████████ 100%

Infrastructure
  requirements/data.txt  ░░░░░░░░░░░░   0%  Chưa tạo
  Dockerfile.data        ░░░░░░░░░░░░   0%  Chưa tạo
  Supabase               ░░░░░░░░░░░░   0%  Chưa setup
  AWS                    ░░░░░░░░░░░░   0%  Chưa bắt đầu

─────────────────────────────────────────
Sẵn sàng deploy:   Chưa
Ước tính thời gian: 4–6 giờ làm việc tập trung
  (bao gồm: fix 2 bugs + tạo 4 files + setup Supabase + test local + push ECR + ECS setup)
```

---

## 7. Điểm cần chú ý đặc biệt

**Về `StockIndicator.symbol = Column("ticker", ...)`:**

DB column sẽ được tạo với tên `ticker` (không phải `symbol`) khi `init_db()` chạy. Điều này có nghĩa là khi query Supabase SQL Editor cần dùng:
```sql
SELECT ticker, trade_date, rsi_14 FROM stock_indicators;  -- đúng
SELECT symbol, trade_date, rsi_14 FROM stock_indicators;  -- sai, column không tồn tại
```

Nhưng trong Python qua ORM: `StockIndicator.symbol` là đúng. Đây là điểm dễ gây nhầm lẫn khi debug.

**Về `UniqueConstraint("ticker", "trade_date")` trong `StockIndicator`:**

Constraint này dùng DB column name `"ticker"` (đúng). Nhưng nếu sau này migrate schema đổi column thành `symbol`, phải drop và recreate constraint.

**Về `ingest_intraday.py` — Cần test runtime:**

File này hoàn chỉnh về logic nhưng chưa được test với vnstock thực. `fetch_intraday_ohlcv()` dùng VCI source và interval `5m` — cần verify VCI hỗ trợ interval này và normalize đúng columns.
