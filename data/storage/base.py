from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import AgentLog, DailySentiment, FinancialRatio, MarketDataDaily, SessionLocal, Symbol


class BaseRepository:
    def __init__(self, session: Session | None = None):
        self.db: Session = session or SessionLocal()

    def close(self) -> None:
        self.db.close()

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> Any:
        return self.db.execute(text(query), params or {})

    def execute_many(self, query: str, params_list: list[dict[str, Any]]) -> Any:
        return self.db.execute(text(query), params_list)

    def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        result = self.execute_query(query, params)
        return [dict(row) for row in result.mappings().all()]

    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        result = self.execute_query(query, params)
        row = result.mappings().first()
        return dict(row) if row is not None else None

    def upsert(
        self,
        model: type,
        match_fields: dict[str, Any],
        values: dict[str, Any],
    ) -> Any:
        instance = self.db.query(model).filter_by(**match_fields).first()
        payload = {**match_fields, **values}
        if instance is None:
            instance = model(**payload)
            self.db.add(instance)
        else:
            for key, value in payload.items():
                setattr(instance, key, value)
        self.db.commit()
        self.db.refresh(instance)
        return instance


class DataRepository(BaseRepository):
    @staticmethod
    def _build_market_record(ticker: str, row: pd.Series) -> MarketDataDaily:
        volume = int(row.get("volume", 0)) if not pd.isna(row.get("volume")) else 0
        buy_foreign = int(row.get("buy_foreign", 0)) if not pd.isna(row.get("buy_foreign")) else 0
        sell_foreign = int(row.get("sell_foreign", 0)) if not pd.isna(row.get("sell_foreign")) else 0
        row_date = pd.to_datetime(row.get("date") or row.get("ts")).to_pydatetime()
        trade_date = pd.Timestamp(row.get("trade_date") or row_date.date()).date()
        return MarketDataDaily(
            ticker=ticker,
            date=row_date,
            trade_date=trade_date,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=volume,
            value=float(row.get("value", 0.0) or 0.0),
            source=str(row.get("source", "vnstock")),
            fetched_at=pd.to_datetime(row.get("fetched_at") or datetime.utcnow()).to_pydatetime(),
            buy_foreign=buy_foreign,
            sell_foreign=sell_foreign,
        )

    def save_daily_data(self, ticker: str, df: pd.DataFrame) -> int:
        if df.empty:
            return 0

        normalized_dates = pd.to_datetime(df["date"] if "date" in df.columns else df["ts"])
        window_start = normalized_dates.min().to_pydatetime()
        window_end = normalized_dates.max().to_pydatetime()
        existing_dates = {
            pd.Timestamp(row[0]).to_pydatetime()
            for row in self.db.query(MarketDataDaily.date)
            .filter(
                MarketDataDaily.ticker == ticker,
                MarketDataDaily.date >= window_start,
                MarketDataDaily.date <= window_end,
            )
            .all()
        }

        count = 0
        new_records = []
        for _, row in df.iterrows():
            row_date = pd.to_datetime(row["date"] if "date" in row else row["ts"]).to_pydatetime()
            if row_date in existing_dates:
                continue
            new_records.append(self._build_market_record(ticker, row))
            existing_dates.add(row_date)
            count += 1

        if new_records:
            self.db.add_all(new_records)
            self.db.commit()

        return count

    def replace_daily_data(self, ticker: str, df: pd.DataFrame) -> int:
        try:
            self.db.query(MarketDataDaily).filter(MarketDataDaily.ticker == ticker).delete(
                synchronize_session=False
            )
            records = [self._build_market_record(ticker, row) for _, row in df.iterrows()]
            if records:
                self.db.add_all(records)
            self.db.commit()
            return len(records)
        except Exception:
            self.db.rollback()
            raise

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
            self.db.query(FinancialRatio).filter(FinancialRatio.ticker == ticker).delete(
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
                    {"ticker": ticker, "quarter": quarter},
                    record,
                )
                count += 1
            return count
        except Exception:
            self.db.rollback()
            raise

    def get_latest_ratio(self, ticker: str, ref_date: datetime | str | None = None) -> FinancialRatio | None:
        try:
            query = self.db.query(FinancialRatio).filter(FinancialRatio.ticker == ticker)
            if ref_date is not None:
                cutoff = pd.to_datetime(ref_date).to_pydatetime()
                ref_quarter = f"{cutoff.year}-Q{((cutoff.month - 1) // 3) + 1}"
                query = query.filter(FinancialRatio.quarter <= ref_quarter)
            return query.order_by(FinancialRatio.quarter.desc()).first()
        except Exception:
            return None

    def upsert_symbol_metadata(self, ticker: str, metadata: dict[str, Any]) -> None:
        self.upsert(Symbol, {"ticker": ticker.upper().strip()}, metadata)

    def get_symbol(self, ticker: str) -> Symbol | None:
        try:
            normalized_ticker = ticker.upper().strip()
            return self.db.query(Symbol).filter(Symbol.ticker == normalized_ticker).first()
        except Exception:
            return None

    def resolve_sector_bucket(self, ticker: str) -> str:
        symbol = self.get_symbol(ticker)
        if symbol is None:
            return "other"

        labels = [
            str(value).strip().lower()
            for value in [symbol.industry, symbol.icb_name2, symbol.icb_name3, symbol.icb_name4]
            if value
        ]
        text_value = " | ".join(labels)
        if any(keyword in text_value for keyword in ["ngan hang", "bank"]):
            return "banking"
        if any(keyword in text_value for keyword in ["bat dong san", "real estate", "real_estate"]):
            return "real_estate"
        if any(keyword in text_value for keyword in ["cong nghe", "phan mem", "technology", "software"]):
            return "technology"
        if any(keyword in text_value for keyword in ["tai nguyen", "vat lieu", "materials", "steel", "chemical"]):
            return "materials"
        if any(keyword in text_value for keyword in ["dau khi", "energy", "oil", "gas", "utility"]):
            return "energy"
        if any(keyword in text_value for keyword in ["ban le", "thuc pham", "consumer", "retail", "beverage"]):
            return "consumer"
        if any(keyword in text_value for keyword in ["van tai", "aviation", "airline", "transport"]):
            return "transport"
        if any(keyword in text_value for keyword in ["bao hiem", "insurance"]):
            return "insurance"
        if any(keyword in text_value for keyword in ["chung khoan", "securities", "brokerage"]):
            return "securities"
        return "other"

    def save_agent_log(self, ticker: str, action: str, confidence: str, reason: str) -> None:
        try:
            log = AgentLog(
                ticker=ticker,
                action=action,
                confidence=confidence,
                reason=reason,
                timestamp=datetime.utcnow(),
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def get_price_history(
        self,
        ticker: str,
        days: int = 3650,
        *,
        start_date: datetime | str | None = None,
        end_date: datetime | str | None = None,
    ) -> pd.DataFrame:
        try:
            query = self.db.query(MarketDataDaily).filter(MarketDataDaily.ticker == ticker)
            if start_date is not None:
                start_ts = pd.to_datetime(start_date).normalize()
                query = query.filter(MarketDataDaily.date >= start_ts.to_pydatetime())
            if end_date is not None:
                end_exclusive = (pd.to_datetime(end_date).normalize() + pd.Timedelta(days=1)).to_pydatetime()
                query = query.filter(MarketDataDaily.date < end_exclusive)
            if days > 0 and start_date is None and end_date is None:
                rows = query.order_by(MarketDataDaily.date.desc()).limit(days).all()
                results = sorted(rows, key=lambda row: row.date)
            else:
                results = query.order_by(MarketDataDaily.date.asc()).all()

            if not results:
                return pd.DataFrame()

            data = [
                {
                    "date": r.date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "buy_foreign": getattr(r, "buy_foreign", 0),
                    "sell_foreign": getattr(r, "sell_foreign", 0),
                }
                for r in results
            ]

            df = pd.DataFrame(data)
            df["date"] = pd.to_datetime(df["date"])
            for column in ["open", "high", "low", "close", "volume", "buy_foreign", "sell_foreign"]:
                df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

            if days > 0 and (start_date is not None or end_date is not None):
                df = df.tail(days)

            return df.reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

    def upsert_daily_sentiment(
        self,
        ticker: str,
        day: datetime,
        daily_score: float,
        confidence: float,
        impact_summary: str,
    ) -> None:
        try:
            self.upsert(
                DailySentiment,
                {"ticker": ticker, "date": day},
                {
                    "daily_score": daily_score,
                    "confidence": confidence,
                    "impact_summary": impact_summary,
                },
            )
        except Exception:
            self.db.rollback()

    def get_decayed_sentiment(self, ticker: str, ref_date: datetime, days_back: int = 5) -> tuple[float, float, int]:
        try:
            start_date = ref_date.replace(hour=0, minute=0, second=0, microsecond=0)
            results = (
                self.db.query(DailySentiment)
                .filter(
                    DailySentiment.ticker == ticker,
                    DailySentiment.date >= start_date - pd.Timedelta(days=days_back - 1),
                    DailySentiment.date <= start_date,
                )
                .order_by(DailySentiment.date.desc())
                .all()
            )
            if not results:
                return 0.0, 0.0, 0

            weights = []
            scores = []
            confidences = []
            for row in results:
                days_diff = (start_date - row.date).days
                weight = 0.5**days_diff
                weights.append(weight)
                scores.append(row.daily_score if row.daily_score is not None else 0.0)
                confidences.append(row.confidence if row.confidence is not None else 0.0)

            total_weight = sum(weights)
            if total_weight == 0:
                return 0.0, 0.0, 0

            weighted_score = sum(score * weight for score, weight in zip(scores, weights)) / total_weight
            weighted_confidence = sum(conf * weight for conf, weight in zip(confidences, weights)) / total_weight
            return float(weighted_score), float(weighted_confidence), len(results)
        except Exception:
            return 0.0, 0.0, 0
