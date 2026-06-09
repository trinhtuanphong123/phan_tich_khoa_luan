from __future__ import annotations

import pandas as pd


def _empty_indicator_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "trade_date",
            "ema_20",
            "ema_50",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_lower",
            "bb_mid",
            "atr_14",
            "volume_sma_20",
        ]
    )


def compute_indicators(ohlcv_df: pd.DataFrame) -> pd.DataFrame:
    if ohlcv_df.empty:
        return _empty_indicator_frame()

    frame = ohlcv_df.copy()
    if "close" not in frame.columns:
        raise ValueError("ohlcv_df must include close")

    if "trade_date" in frame.columns:
        frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.date
    elif "ts" in frame.columns:
        frame["trade_date"] = pd.to_datetime(frame["ts"], errors="coerce").dt.date
    else:
        raise ValueError("ohlcv_df must include trade_date or ts")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["high"] = pd.to_numeric(frame.get("high"), errors="coerce")
    frame["low"] = pd.to_numeric(frame.get("low"), errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume"), errors="coerce")
    frame = frame.sort_values("trade_date").reset_index(drop=True)

    close = frame["close"]
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.rolling(14, min_periods=14).mean()
    avg_loss = loss.rolling(14, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    frame["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))
    frame["ema_20"] = close.ewm(span=20, adjust=False, min_periods=20).mean()
    frame["ema_50"] = close.ewm(span=50, adjust=False, min_periods=50).mean()

    ema_12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema_26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    frame["macd_line"] = ema_12 - ema_26
    frame["macd_signal"] = frame["macd_line"].ewm(span=9, adjust=False, min_periods=9).mean()
    frame["macd_hist"] = frame["macd_line"] - frame["macd_signal"]

    rolling_mean = close.rolling(20, min_periods=20).mean()
    rolling_std = close.rolling(20, min_periods=20).std()
    frame["bb_mid"] = rolling_mean
    frame["bb_upper"] = rolling_mean + (2.0 * rolling_std)
    frame["bb_lower"] = rolling_mean - (2.0 * rolling_std)

    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr_14"] = true_range.rolling(14, min_periods=14).mean()
    frame["volume_sma_20"] = frame["volume"].rolling(20, min_periods=20).mean()

    return frame[
        [
            "trade_date",
            "ema_20",
            "ema_50",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "bb_upper",
            "bb_lower",
            "bb_mid",
            "atr_14",
            "volume_sma_20",
        ]
    ].copy()
