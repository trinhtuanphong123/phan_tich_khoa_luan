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