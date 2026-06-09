from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .base import BaseRepository
from .models import FinancialRatio


class RatioRepository(BaseRepository):
    @staticmethod
    def _to_ratio_value(value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        numeric = pd.to_numeric(value, errors="coerce")
        if pd.isna(numeric):
            return None
        return float(numeric)

    @staticmethod
    def _growth_pct(current: float | None, previous: float | None) -> float | None:
        if current is None or previous is None or previous == 0:
            return None
        return ((current - previous) / abs(previous)) * 100.0

    def replace_financial_ratios(self, ticker: str, records: list[dict[str, Any]]) -> int:
        try:
            self.db.query(FinancialRatio).filter(FinancialRatio.symbol == ticker).delete(
                synchronize_session=False
            )
            ratio_rows = [FinancialRatio(**record) for record in records]
            if ratio_rows:
                self.db.add_all(ratio_rows)
            self.db.commit()
            return len(ratio_rows)
        except Exception:
            self.db.rollback()
            raise

    def save_financial_ratios(self, ticker: str, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        count = 0
        try:
            for record in records:
                quarter = str(record.get("quarter", "")).strip()
                if not quarter:
                    continue
                self.upsert(
                    FinancialRatio,
                    {"symbol": ticker, "quarter": quarter},
                    record,
                )
                count += 1
            return count
        except Exception:
            self.db.rollback()
            raise

    def get_latest_ratio(self, ticker: str, ref_date: datetime | str | None = None) -> FinancialRatio | None:
        try:
            query = self.db.query(FinancialRatio).filter(FinancialRatio.symbol == ticker)
            if ref_date is not None:
                cutoff = pd.to_datetime(ref_date).to_pydatetime()
                ref_quarter = f"{cutoff.year}-Q{((cutoff.month - 1) // 3) + 1}"
                query = query.filter(FinancialRatio.quarter <= ref_quarter)
            return query.order_by(FinancialRatio.quarter.desc()).first()
        except Exception:
            return None
