from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from uuid import uuid4

from dotenv import load_dotenv

from config import PROJECT_ROOT
from data.features.feature_store import save_market_features
from data.features.indicators import compute_indicators
from data.features.market_features import build_market_feature_matrix
from data.market.repository import get_daily_ohlcv
from data.market.universe import get_priority_symbols
from data.storage.indicator_repo import save_stock_indicators
from data.storage.models import FeatureRun, SessionLocal


def _create_feature_run(run_id: str, lookback_days: int, symbol_count: int) -> None:
    session = SessionLocal()
    try:
        session.add(
            FeatureRun(
                run_id=run_id,
                feature_set="market_features_and_indicators",
                status="running",
                metadata_json={
                    "lookback_days": lookback_days,
                    "symbol_count": symbol_count,
                },
            )
        )
        session.commit()
    finally:
        session.close()


def _finish_feature_run(
    run_id: str,
    *,
    status: str,
    artifact_path: str | None,
    feature_rows: int,
    feature_columns: int,
    indicator_rows: int,
    symbols_success: int,
    symbols_failed: int,
    errors: list[dict[str, str]],
) -> None:
    session = SessionLocal()
    try:
        run = session.query(FeatureRun).filter(FeatureRun.run_id == run_id).first()
        if run is None:
            return
        metadata = dict(run.metadata_json or {})
        metadata.update(
            {
                "feature_rows": feature_rows,
                "feature_columns": feature_columns,
                "indicator_rows": indicator_rows,
                "symbols_success": symbols_success,
                "symbols_failed": symbols_failed,
                "errors": errors,
            }
        )
        run.finished_at = datetime.utcnow()
        run.status = status
        run.artifact_path = artifact_path
        run.metadata_json = metadata
        session.commit()
    finally:
        session.close()


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    symbols = get_priority_symbols()
    end_date = date.today()
    lookback_days = int(os.getenv("INDICATOR_LOOKBACK_DAYS", "252"))
    start_date = end_date - timedelta(days=lookback_days - 1)
    run_id = f"feature-run-{end_date.isoformat()}-{uuid4().hex[:8]}"

    _create_feature_run(run_id, lookback_days, len(symbols))
    try:
        feature_matrix = build_market_feature_matrix(symbols, end_date, lookback_days)
        artifact = save_market_features(run_id, feature_matrix)

        total_indicator_rows = 0
        symbols_success = 0
        symbols_failed = 0
        errors: list[dict[str, str]] = []

        for symbol in symbols:
            try:
                ohlcv_df = get_daily_ohlcv([symbol], start_date, end_date)
                if ohlcv_df.empty:
                    raise ValueError("no daily OHLCV returned")

                indicator_df = compute_indicators(ohlcv_df)
                rows_written = save_stock_indicators(symbol, indicator_df)
                total_indicator_rows += rows_written
                symbols_success += 1
                print(f"{symbol}: indicators_saved={rows_written}")
            except Exception as exc:
                symbols_failed += 1
                errors.append({"symbol": symbol, "error": str(exc)})
                print(f"{symbol}: indicator_build_failed error={exc}")

        status = "success" if symbols_failed == 0 else "partial_success"
        _finish_feature_run(
            run_id,
            status=status,
            artifact_path=str(artifact.path),
            feature_rows=int(len(feature_matrix.index)),
            feature_columns=int(len(feature_matrix.columns)),
            indicator_rows=total_indicator_rows,
            symbols_success=symbols_success,
            symbols_failed=symbols_failed,
            errors=errors,
        )

        print(
            "feature_build_summary "
            f"run_id={run_id} "
            f"symbols={len(symbols)} "
            f"symbols_success={symbols_success} "
            f"symbols_failed={symbols_failed} "
            f"feature_rows={len(feature_matrix.index)} "
            f"feature_columns={len(feature_matrix.columns)} "
            f"indicator_rows={total_indicator_rows} "
            f"artifact_path={artifact.path}"
        )
    except Exception as exc:
        _finish_feature_run(
            run_id,
            status="failed",
            artifact_path=None,
            feature_rows=0,
            feature_columns=0,
            indicator_rows=0,
            symbols_success=0,
            symbols_failed=len(symbols),
            errors=[{"symbol": "*", "error": str(exc)}],
        )
        raise


if __name__ == "__main__":
    main()
