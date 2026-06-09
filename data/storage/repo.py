from __future__ import annotations

from .agent_log_repo import AgentLogRepository
from .base import BaseRepository
from .ratio_repo import RatioRepository
from .sentiment_repo import SentimentRepository
from .symbol_repo import SymbolRepository


class DataRepository(
    RatioRepository,
    SymbolRepository,
    SentimentRepository,
    AgentLogRepository,
):
    """Compatibility facade for legacy callers that still expect one repository object."""

__all__ = ["BaseRepository", "DataRepository"]
