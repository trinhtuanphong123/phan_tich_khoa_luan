from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pandas as pd

from .models import ClusterRun, SessionLocal, StockCluster


def _to_dataframe(rows: pd.DataFrame | list[dict[str, object]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.DataFrame(rows)


def create_cluster_run(
    feature_run_id: int | None = None,
    algorithm: str | None = None,
    metadata: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> str:
    session = SessionLocal()
    try:
        resolved_run_id = run_id or f"cluster-{uuid.uuid4().hex[:12]}"
        row = ClusterRun(
            run_id=resolved_run_id,
            feature_run_id=feature_run_id,
            started_at=datetime.utcnow(),
            status="running",
            algorithm=algorithm,
            metadata_json=metadata or {},
        )
        session.add(row)
        session.commit()
        return resolved_run_id
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_stock_clusters(run_id: str, rows: pd.DataFrame | list[dict[str, object]], status: str = "completed") -> int:
    frame = _to_dataframe(rows)
    if frame.empty:
        return 0

    session = SessionLocal()
    try:
        cluster_run = session.query(ClusterRun).filter(ClusterRun.run_id == run_id).first()
        if cluster_run is None:
            raise ValueError(f"cluster run not found: {run_id}")

        session.query(StockCluster).filter(StockCluster.cluster_run_id == cluster_run.id).delete(
            synchronize_session=False
        )

        count = 0
        for _, row in frame.iterrows():
            session.add(
                StockCluster(
                    cluster_run_id=cluster_run.id,
                    symbol=str(row["symbol"]).strip().upper(),
                    cluster_label=str(row["cluster_label"]),
                    score=None if pd.isna(row.get("score")) else float(row.get("score")),
                    created_at=datetime.utcnow(),
                )
            )
            count += 1

        cluster_run.status = status
        cluster_run.finished_at = datetime.utcnow()
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_latest_clusters() -> pd.DataFrame:
    session = SessionLocal()
    try:
        latest_run = session.query(ClusterRun).order_by(ClusterRun.started_at.desc()).first()
        if latest_run is None:
            return pd.DataFrame()

        rows = (
            session.query(StockCluster)
            .filter(StockCluster.cluster_run_id == latest_run.id)
            .order_by(StockCluster.symbol.asc())
            .all()
        )
    finally:
        session.close()

    return pd.DataFrame(
        [
            {
                "run_id": latest_run.run_id,
                "symbol": row.symbol,
                "cluster_label": row.cluster_label,
                "score": row.score,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    )


def get_cluster_runs() -> pd.DataFrame:
    session = SessionLocal()
    try:
        rows = session.query(ClusterRun).order_by(ClusterRun.started_at.desc()).all()
    finally:
        session.close()

    return pd.DataFrame(
        [
            {
                "run_id": row.run_id,
                "feature_run_id": row.feature_run_id,
                "started_at": row.started_at,
                "finished_at": row.finished_at,
                "status": row.status,
                "algorithm": row.algorithm,
                "metadata_json": row.metadata_json,
            }
            for row in rows
        ]
    )


def get_stock_cluster_history(ticker: str) -> pd.DataFrame:
    normalized_ticker = ticker.strip().upper()
    session = SessionLocal()
    try:
        rows = (
            session.query(StockCluster, ClusterRun)
            .join(ClusterRun, StockCluster.cluster_run_id == ClusterRun.id)
            .filter(StockCluster.symbol == normalized_ticker)
            .order_by(ClusterRun.started_at.asc())
            .all()
        )
    finally:
        session.close()

    return pd.DataFrame(
        [
            {
                "run_id": cluster_run.run_id,
                "symbol": stock_cluster.symbol,
                "cluster_label": stock_cluster.cluster_label,
                "score": stock_cluster.score,
                "started_at": cluster_run.started_at,
                "finished_at": cluster_run.finished_at,
                "status": cluster_run.status,
            }
            for stock_cluster, cluster_run in rows
        ]
    )
