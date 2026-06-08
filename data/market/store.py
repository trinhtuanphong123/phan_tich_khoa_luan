from __future__ import annotations

from typing import Any

import pandas as pd

from data.market.validator import ValidationResult, validate_daily, validate_intraday
from data.storage import market_repo


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def _store_rows(
    rows: pd.DataFrame | list[dict[str, object]],
    *,
    validator,
    upsert_fn,
) -> dict[str, Any]:
    frame = _to_dataframe(rows)
    validation: ValidationResult = validator(frame)

    stored_row_count = 0
    if not validation.valid_rows.empty:
        upsert_fn(validation.valid_rows)
        stored_row_count = int(len(validation.valid_rows))

    quality_report = dict(validation.quality_report)
    quality_report["stored_row_count"] = stored_row_count

    return {
        "valid_rows": validation.valid_rows,
        "invalid_rows": validation.invalid_rows,
        "quality_report": quality_report,
    }


def store_intraday_rows(rows: pd.DataFrame | list[dict[str, object]]) -> dict[str, Any]:
    return _store_rows(
        rows,
        validator=validate_intraday,
        upsert_fn=market_repo.upsert_ohlcv_5m,
    )


def store_daily_rows(rows: pd.DataFrame | list[dict[str, object]]) -> dict[str, Any]:
    return _store_rows(
        rows,
        validator=validate_daily,
        upsert_fn=market_repo.upsert_ohlcv_1d,
    )
