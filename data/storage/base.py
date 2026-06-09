from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import SessionLocal


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
