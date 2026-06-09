from __future__ import annotations

from datetime import datetime

import pandas as pd

from .base import BaseRepository
from .models import DailySentiment


class SentimentRepository(BaseRepository):
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
                {"symbol": ticker, "date": day},
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
                    DailySentiment.symbol == ticker,
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
