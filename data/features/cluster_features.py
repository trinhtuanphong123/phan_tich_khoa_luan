from __future__ import annotations

import pandas as pd

from data.features.market_features import build_market_feature_matrix


def _get_feature_slice(feature_matrix: pd.DataFrame, feature_name: str) -> pd.DataFrame:
    if feature_matrix.empty:
        return pd.DataFrame()

    if not isinstance(feature_matrix.columns, pd.MultiIndex):
        raise ValueError("feature_matrix must use MultiIndex columns: (feature_name, symbol)")

    if feature_name not in feature_matrix.columns.get_level_values(0):
        return pd.DataFrame()

    sliced = feature_matrix[feature_name].copy()
    sliced.index.name = feature_matrix.index.name
    return sliced.sort_index(axis=1)


def build_cluster_input_matrix(
    symbols: list[str] | tuple[str, ...] | set[str],
    end_date,
    lookback_days: int,
    feature_name: str = "log_return",
) -> pd.DataFrame:
    feature_matrix = build_market_feature_matrix(symbols, end_date, lookback_days)
    return _get_feature_slice(feature_matrix, feature_name)


def build_latest_feature_snapshot(
    feature_matrix: pd.DataFrame,
    feature_name: str = "log_return",
) -> pd.Series:
    sliced = _get_feature_slice(feature_matrix, feature_name)
    if sliced.empty:
        return pd.Series(dtype="float64")
    return sliced.iloc[-1].dropna()


def build_correlation_similarity_matrix(feature_matrix: pd.DataFrame) -> pd.DataFrame:
    if feature_matrix.empty:
        return pd.DataFrame()
    return feature_matrix.corr(method="pearson").fillna(0.0)
