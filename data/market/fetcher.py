from __future__ import annotations

import io
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _format_daily_date(value: date | datetime | str) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _format_timestamp(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def _base_external_vnstock_script() -> list[str]:
    return [
        "import os",
        "import site",
        "import sys",
        f"project_root = {str(PROJECT_ROOT)!r}",
        "filtered = []",
        "for path in sys.path:",
        "    resolved = os.path.abspath(path or '.')",
        "    if resolved == project_root or resolved.startswith(os.path.join(project_root, 'vnstock')):",
        "        continue",
        "    filtered.append(path)",
        "for package_dir in site.getsitepackages():",
        "    if package_dir not in filtered:",
        "        filtered.insert(0, package_dir)",
        "sys.path = filtered",
    ]


def _extract_json_array(output: str) -> str:
    start = output.find("[")
    end = output.rfind("]")
    if start == -1 or end == -1 or end < start:
        return ""
    return output[start : end + 1]


def _run_vnstock_history_script(
    *,
    symbol: str,
    start_value: str,
    end_value: str,
    interval: str,
    source: str,
    use_kbs_stock_wrapper: bool,
) -> pd.DataFrame:
    script_lines = _base_external_vnstock_script()
    script_lines.extend(
        [
            f"symbol = {symbol.strip().upper()!r}",
            f"start_value = {start_value!r}",
            f"end_value = {end_value!r}",
            f"interval = {interval!r}",
            f"source = {source!r}",
        ]
    )
    if use_kbs_stock_wrapper:
        script_lines.extend(
            [
                "from vnstock import Vnstock",
                "df = Vnstock().stock(symbol=symbol, source=source).quote.history(",
                "    start=start_value,",
                "    end=end_value,",
                "    interval=interval,",
                "    get_all=True,",
                ")",
            ]
        )
    else:
        script_lines.extend(
            [
                "from vnstock import Quote",
                "df = Quote(symbol=symbol, source=source).history(",
                "    start=start_value,",
                "    end=end_value,",
                "    interval=interval,",
                ")",
            ]
        )
    script_lines.extend(
        [
            "if df is None or df.empty:",
            "    print('[]')",
            "else:",
            "    print(df.to_json(orient='records', date_format='iso'))",
        ]
    )

    env = os.environ.copy()
    if os.getenv("VNSTOCK_API_KEY"):
        env["VNSTOCK_API_KEY"] = os.getenv("VNSTOCK_API_KEY", "")

    result = subprocess.run(
        [sys.executable, "-c", "\n".join(script_lines)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    output = _extract_json_array(result.stdout.strip())
    if not output:
        return pd.DataFrame()
    return pd.read_json(io.StringIO(output), orient="records")


def fetch_daily_ohlcv(
    symbol: str,
    start_date: date | datetime | str,
    end_date: date | datetime | str,
) -> pd.DataFrame:
    return _run_vnstock_history_script(
        symbol=symbol,
        start_value=_format_daily_date(start_date),
        end_value=_format_daily_date(end_date),
        interval="1D",
        source=os.getenv("VNSTOCK_DAILY_SOURCE", "KBS"),
        use_kbs_stock_wrapper=True,
    )


def fetch_intraday_ohlcv(
    symbol: str,
    start_ts: datetime | str,
    end_ts: datetime | str,
    interval: str = "5m",
) -> pd.DataFrame:
    return _run_vnstock_history_script(
        symbol=symbol,
        start_value=_format_timestamp(start_ts),
        end_value=_format_timestamp(end_ts),
        interval=interval,
        source=os.getenv("VNSTOCK_INTRADAY_SOURCE", "VCI"),
        use_kbs_stock_wrapper=False,
    )


def fetch_symbol_batch(
    symbols: list[str],
    start_ts: datetime | str,
    end_ts: datetime | str,
    interval: str,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for symbol in symbols:
        df = fetch_intraday_ohlcv(symbol, start_ts, end_ts, interval=interval)
        records.append(
            {
                "symbol": symbol.strip().upper(),
                "records": df.to_dict(orient="records"),
            }
        )
    return records
