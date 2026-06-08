from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from config import paths
from data.features.schemas import FeatureArtifact


FEATURE_ARTIFACTS_DIR = paths.data_dir / "feature_artifacts"
FEATURE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _feature_matrix_path(run_id: str) -> Path:
    return FEATURE_ARTIFACTS_DIR / f"{run_id}.pkl"


def _feature_metadata_path(run_id: str) -> Path:
    return FEATURE_ARTIFACTS_DIR / f"{run_id}.json"


def save_feature_matrix_artifact(run_id: str, df: pd.DataFrame) -> FeatureArtifact:
    path = _feature_matrix_path(run_id)
    df.to_pickle(path)

    artifact = FeatureArtifact(
        run_id=run_id,
        path=path,
        row_count=int(len(df)),
        column_count=int(len(df.columns)),
        created_at=datetime.now(),
    )

    metadata_path = _feature_metadata_path(run_id)
    metadata_path.write_text(
        json.dumps(
            {
                "run_id": artifact.run_id,
                "path": str(artifact.path),
                "row_count": artifact.row_count,
                "column_count": artifact.column_count,
                "created_at": artifact.created_at.isoformat(timespec="seconds"),
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    return artifact


def save_market_features(run_id: str, features: pd.DataFrame) -> FeatureArtifact:
    return save_feature_matrix_artifact(run_id, features)


def load_market_features(run_id: str) -> pd.DataFrame:
    path = _feature_matrix_path(run_id)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_pickle(path)
