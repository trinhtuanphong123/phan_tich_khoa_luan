from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class MarketBar5m:
    symbol: str
    ts: datetime
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | int | None
    value: float | None = None
    source: str = "vnstock"
    fetched_at: datetime | None = None


@dataclass(frozen=True)
class MarketBar1d:
    symbol: str
    ts: datetime
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | int | None
    value: float | None = None
    source: str = "vnstock"
    fetched_at: datetime | None = None


@dataclass(frozen=True)
class MarketFetchRequest:
    symbols: list[str]
    interval: str
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    source: str = "vnstock"
    api_key: str | None = None
    extra_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketQualityReport:
    total_rows: int
    valid_row_count: int
    invalid_row_count: int
    error_counts: dict[str, int] = field(default_factory=dict)
    stored_row_count: int = 0


@dataclass(frozen=True)
class MarketFetchResult:
    request: MarketFetchRequest
    records: list[MarketBar5m | MarketBar1d] = field(default_factory=list)
    invalid_rows: list[dict[str, Any]] = field(default_factory=list)
    quality_report: MarketQualityReport | None = None
