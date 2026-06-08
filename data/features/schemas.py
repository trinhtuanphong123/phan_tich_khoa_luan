from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class FeatureBuildRequest:
    symbols: list[str]
    end_date: date | datetime | str
    lookback_days: int
    feature_names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FeatureMatrix:
    run_id: str
    frame: pd.DataFrame
    feature_names: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FeatureArtifact:
    run_id: str
    path: Path
    row_count: int
    column_count: int
    created_at: datetime
