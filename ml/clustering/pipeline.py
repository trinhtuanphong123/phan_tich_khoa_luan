from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from data.features.market_features import build_market_feature_matrix
from data.storage.models import FeatureRun, SessionLocal


def _get_feature_run(run_id: str) -> FeatureRun:
    session = SessionLocal()
    try:
        run = session.query(FeatureRun).filter(FeatureRun.run_id == run_id).first()
        if run is None:
            raise ValueError(f"feature run not found: {run_id}")
        return run
    finally:
        session.close()


def _parse_end_date(run: FeatureRun, metadata: dict[str, Any]) -> date:
    end_date = metadata.get("end_date")
    if isinstance(end_date, str) and end_date.strip():
        return date.fromisoformat(end_date)

    parts = run.run_id.split("-")
    if len(parts) >= 4:
        return date.fromisoformat(parts[2])

    raise ValueError(f"feature run missing end_date metadata: {run.run_id}")


def _parse_symbols(run: FeatureRun, metadata: dict[str, Any]) -> list[str]:
    symbols = metadata.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        raise ValueError(
            f"feature run missing symbols metadata; cannot rebuild from DB: {run.run_id}"
        )

    normalized = sorted(
        {
            str(symbol).strip().upper()
            for symbol in symbols
            if str(symbol).strip()
        }
    )
    if not normalized:
        raise ValueError(
            f"feature run symbols metadata is empty after normalization: {run.run_id}"
        )
    return normalized


def _parse_lookback_days(run: FeatureRun, metadata: dict[str, Any]) -> int:
    lookback_days = metadata.get("lookback_days")
    try:
        resolved = int(lookback_days)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"feature run missing valid lookback_days metadata: {run.run_id}"
        ) from exc
    if resolved <= 0:
        raise ValueError(f"feature run lookback_days must be positive: {run.run_id}")
    return resolved


def load_feature_matrix_from_db(run_id: str) -> pd.DataFrame:
    run = _get_feature_run(run_id)
    metadata = dict(run.metadata_json or {})
    symbols = _parse_symbols(run, metadata)
    end_date = _parse_end_date(run, metadata)
    lookback_days = _parse_lookback_days(run, metadata)
    return build_market_feature_matrix(symbols, end_date, lookback_days)
