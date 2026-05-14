from __future__ import annotations

from typing import TypedDict

import pandas as pd

# 0.0 — без допуска (строгое пересечение). Для размытия вернуть, напр., 0.001.
THRESHOLD = 0.0

class CrossSignalFlags(TypedDict):
    bullish: bool
    bearish: bool

class Signals(TypedDict):
    ema_4_8: CrossSignalFlags
    ema_8_16: CrossSignalFlags
    macd: CrossSignalFlags
    has_some_signal: bool

class SignalChecker:
    def __init__(self, threshold: float = THRESHOLD) -> None:
        self._threshold = threshold

    def _pair_cross_bullish_bearish(
        self,
        df: pd.DataFrame,
        fast_col: str,
        slow_col: str,
    ) -> CrossSignalFlags:
        if fast_col not in df.columns or slow_col not in df.columns:
            return {"bullish": False, "bearish": False}

        clean_df = df.dropna(subset=[fast_col, slow_col]).copy()

        if len(clean_df) < 2:
            return {"bullish": False, "bearish": False}

        last_candle = clean_df.iloc[-1]
        previous_candle = clean_df.iloc[-2]
        t = self._threshold

        is_bullish_raw = (
            last_candle[fast_col] >= last_candle[slow_col] - t
            and previous_candle[fast_col] <= previous_candle[slow_col] + t
        )

        is_bearish_raw = (
            last_candle[fast_col] <= last_candle[slow_col] + t
            and previous_candle[fast_col] >= previous_candle[slow_col] - t
        )

        if is_bullish_raw and is_bearish_raw:
            prev_gap = float(previous_candle[fast_col] - previous_candle[slow_col])
            last_gap = float(last_candle[fast_col] - last_candle[slow_col])

            drift = last_gap - prev_gap

            if drift > 0:
                return {"bullish": True, "bearish": False}
            if drift < 0:
                return {"bullish": False, "bearish": True}

            return {"bullish": False, "bearish": False}

        if is_bullish_raw:
            return {"bullish": True, "bearish": False}

        if is_bearish_raw:
            return {"bullish": False, "bearish": True}

        return {"bullish": False, "bearish": False}

    def check_ema_4_8(self, df: pd.DataFrame) -> CrossSignalFlags:
        return self._pair_cross_bullish_bearish(df, "EMA_4", "EMA_8")

    def check_ema_8_16(self, df: pd.DataFrame) -> CrossSignalFlags:
        return self._pair_cross_bullish_bearish(df, "EMA_8", "EMA_16")

    def check_macd(self, df: pd.DataFrame) -> CrossSignalFlags:
        return self._pair_cross_bullish_bearish(df, "MACD_12_26_9", "MACDs_12_26_9")

    def check_all(self, df: pd.DataFrame) -> Signals:
        ema_4_8 = self.check_ema_4_8(df)
        ema_8_16 = self.check_ema_8_16(df)
        macd = self.check_macd(df)

        return {
            "ema_4_8": ema_4_8,
            "ema_8_16": ema_8_16,
            "macd": macd,
            "has_some_signal": (
                ema_4_8["bullish"]
                or ema_4_8["bearish"]
                or ema_8_16["bullish"]
                or ema_8_16["bearish"]
                or macd["bullish"]
                or macd["bearish"]
            ),
        }
