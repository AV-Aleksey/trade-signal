from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Literal, TypedDict

import pandas as pd

class FilterFlags(TypedDict):
    confirm: bool
    block: bool

class Filters(TypedDict):
    ema_75: FilterFlags
    rsi_15: FilterFlags
    stochastic_5_3_3: FilterFlags
    stochastic_7_5_3: FilterFlags
    macd_4_5_3: FilterFlags
    bollinger_20_2: FilterFlags

FilterName = Literal[
    "ema_75",
    "rsi_15",
    "stochastic_5_3_3",
    "stochastic_7_5_3",
    "macd_4_5_3",
    "bollinger_20_2",
]

class FilterChecker:
    def __init__(self) -> None:
        self._handlers: dict[FilterName, Callable[[pd.DataFrame], FilterFlags]] = {
            "ema_75": self.check_ema_75,
            "rsi_15": self.check_rsi_15,
            "stochastic_5_3_3": self.check_stochastic_5_3_3,
            "stochastic_7_5_3": self.check_stochastic_7_5_3,
            "macd_4_5_3": self.check_macd_4_5_3,
            "bollinger_20_2": self.check_bollinger_20_2,
        }

    @staticmethod
    def _neutral_flags() -> FilterFlags:
        return {"confirm": False, "block": False}

    @staticmethod
    def _flags_from_comparison(value: float, reference: float) -> FilterFlags:
        if value > reference:
            return {"confirm": True, "block": False}

        if value < reference:
            return {"confirm": False, "block": True}

        return FilterChecker._neutral_flags()

    def _last_value(self, df: pd.DataFrame, column: str) -> float | None:
        if column not in df.columns:
            return None

        clean = df.dropna(subset=[column])

        if clean.empty:
            return None

        return float(clean.iloc[-1][column])

    def check_ema_75(self, df: pd.DataFrame) -> FilterFlags:
        close = self._last_value(df, "close")
        ema_75 = self._last_value(df, "EMA_75")

        if close is None or ema_75 is None:
            return self._neutral_flags()

        return self._flags_from_comparison(close, ema_75)

    def check_rsi_15(self, df: pd.DataFrame) -> FilterFlags:
        rsi = self._last_value(df, "RSI_15")

        if rsi is None:
            return self._neutral_flags()

        return self._flags_from_comparison(rsi, 50.0)

    def check_stochastic_5_3_3(self, df: pd.DataFrame) -> FilterFlags:
        k_val = self._last_value(df, "STOCHk_5_3_3")

        if k_val is None:
            return self._neutral_flags()

        return self._flags_from_comparison(k_val, 50.0)

    def check_stochastic_7_5_3(self, df: pd.DataFrame) -> FilterFlags:
        k_val = self._last_value(df, "STOCHk_7_5_3")

        if k_val is None:
            return self._neutral_flags()

        return self._flags_from_comparison(k_val, 50.0)

    def check_macd_4_5_3(self, df: pd.DataFrame) -> FilterFlags:
        hist = self._last_value(df, "MACDh_4_5_3")

        if hist is None:
            return self._neutral_flags()

        return self._flags_from_comparison(hist, 0.0)

    def check_bollinger_20_2(self, df: pd.DataFrame) -> FilterFlags:
        close = self._last_value(df, "close")
        mid = self._last_value(df, "BBM_20_2.0")

        if close is None or mid is None:
            return self._neutral_flags()

        return self._flags_from_comparison(close, mid)

    def check(
        self,
        df: pd.DataFrame,
        filters: Sequence[FilterName] | None = None,
    ) -> dict[FilterName, FilterFlags]:
        keys = self._handlers if filters is None else filters
        result: dict[FilterName, FilterFlags] = {}

        for key in keys:
            handler = self._handlers.get(key)

            if handler is None:
                continue

            result[key] = handler(df)

        return result
