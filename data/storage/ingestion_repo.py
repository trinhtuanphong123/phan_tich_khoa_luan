from __future__ import annotations

from datetime import datetime

import pandas as pd

from .models import IngestionError, IngestionRun, IngestionWatermark, SessionLocal


def _to_timestamp(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    return pd.Timestamp(value).to_pydatetime()


def start_run(job_type: str, interval: str, window_start: datetime | str | None, window_end: datetime | str | None) -> int:
    session = SessionLocal()
    try:
        run = IngestionRun(
            run_type=job_type,
            interval=interval,
            window_start=_to_timestamp(window_start),
            window_end=_to_timestamp(window_end),
            started_at=datetime.utcnow(),
            status="running",
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return int(run.id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def finish_run(run_id: int, status: str, rows_written: int, symbols_success: int, symbols_failed: int) -> None:
    session = SessionLocal()
    try:
        run = session.query(IngestionRun).filter(IngestionRun.id == run_id).first()
        if run is None:
            raise ValueError(f"ingestion run not found: {run_id}")
        run.status = status
        run.rows_written = int(rows_written)
        run.symbols_success = int(symbols_success)
        run.symbols_failed = int(symbols_failed)
        run.finished_at = datetime.utcnow()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def record_error(run_id: int, symbol: str, error_type: str, error_message: str) -> int:
    session = SessionLocal()
    try:
        error = IngestionError(
            run_id=run_id,
            symbol=symbol.strip().upper() if symbol else None,
            error_type=error_type,
            error_message=error_message,
            created_at=datetime.utcnow(),
        )
        session.add(error)
        session.commit()
        session.refresh(error)
        return int(error.id)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_watermark(symbol: str, interval: str) -> datetime | None:
    session = SessionLocal()
    try:
        row = (
            session.query(IngestionWatermark)
            .filter(
                IngestionWatermark.symbol == symbol.strip().upper(),
                IngestionWatermark.interval == interval,
            )
            .first()
        )
        return row.last_success_ts if row is not None else None
    finally:
        session.close()


def update_watermark(symbol: str, interval: str, last_success_ts: datetime | str) -> None:
    session = SessionLocal()
    try:
        normalized_symbol = symbol.strip().upper()
        normalized_ts = _to_timestamp(last_success_ts)
        row = (
            session.query(IngestionWatermark)
            .filter(
                IngestionWatermark.symbol == normalized_symbol,
                IngestionWatermark.interval == interval,
            )
            .first()
        )
        if row is None:
            row = IngestionWatermark(
                symbol=normalized_symbol,
                interval=interval,
                last_success_ts=normalized_ts,
                updated_at=datetime.utcnow(),
            )
            session.add(row)
        else:
            row.last_success_ts = normalized_ts
            row.updated_at = datetime.utcnow()
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
