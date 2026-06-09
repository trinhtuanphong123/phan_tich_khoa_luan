from __future__ import annotations

from datetime import datetime

from .base import BaseRepository
from .models import AgentLog


class AgentLogRepository(BaseRepository):
    def save_agent_log(self, ticker: str, action: str, confidence: str, reason: str) -> None:
        try:
            log = AgentLog(
                symbol=ticker,
                action=action,
                confidence=confidence,
                reason=reason,
                timestamp=datetime.utcnow(),
            )
            self.db.add(log)
            self.db.commit()
        except Exception:
            self.db.rollback()
