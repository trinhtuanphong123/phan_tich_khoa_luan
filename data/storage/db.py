from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL_ENV = "DATABASE_URL"

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker[Session] | None = None


def _get_database_url() -> str:
    database_url = os.getenv(DATABASE_URL_ENV)
    if not database_url or not database_url.strip():
        raise ValueError(f"{DATABASE_URL_ENV} is required")
    return database_url.strip()


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = create_engine(
            _get_database_url(),
            pool_pre_ping=True,
            future=True,
        )
    return _ENGINE


def get_session() -> Session:
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            future=True,
        )
    return _SESSION_FACTORY()


def health_check() -> bool:
    engine = get_engine()
    with engine.connect() as connection:
        return bool(connection.execute(text("select 1")).scalar_one() == 1)
