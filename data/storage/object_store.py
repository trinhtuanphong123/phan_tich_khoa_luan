from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from config import paths


OBJECT_STORE_ROOT = paths.data_dir / "object_store"
OBJECT_STORE_ROOT.mkdir(parents=True, exist_ok=True)


def _resolve_remote_path(remote_path: str) -> Path:
    normalized = remote_path.strip().replace("\\", "/").lstrip("/")
    path = OBJECT_STORE_ROOT / normalized
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def upload_json(path: str, data: Any) -> Path:
    target = _resolve_remote_path(path)
    target.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    return target


def upload_dataframe(path: str, df: pd.DataFrame) -> Path:
    target = _resolve_remote_path(path)
    suffix = target.suffix.lower()
    if suffix == ".csv":
        df.to_csv(target, index=True)
    elif suffix == ".json":
        df.to_json(target, orient="split", date_format="iso")
    else:
        if not suffix:
            target = target.with_suffix(".pkl")
        df.to_pickle(target)
    return target


def upload_file(local_path: str | Path, remote_path: str) -> Path:
    source = Path(local_path)
    target = _resolve_remote_path(remote_path)
    shutil.copy2(source, target)
    return target


def download_file(remote_path: str, local_path: str | Path | None = None) -> Path:
    source = _resolve_remote_path(remote_path)
    if local_path is None:
        return source

    target = Path(local_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return target
