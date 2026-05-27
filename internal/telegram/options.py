from __future__ import annotations

from typing import Iterable


DEFAULT_PICK_PAIRS: list[str] = ["GB/USDJPY", "GB/EURUSD", "GB/XAUUSD"]

DEFAULT_TICK_OPTIONS: list[dict[str, int]] = [
    {"label": "1 минута", "value": 1},
    {"label": "5 минут", "value": 2},
    {"label": "15 минут", "value": 3},
    {"label": "30 минут", "value": 4},
    {"label": "1 час", "value": 5},
    {"label": "2 часа", "value": 6},
    {"label": "4 часа", "value": 7},
    {"label": "День", "value": 8},
    {"label": "Неделя", "value": 9},
]

DEFAULT_SIGNAL_OPTIONS: list[dict[str, str]] = [
    {"label": "EMA 4 / EMA 8", "value": "ema_4_8"},
    {"label": "EMA 8 / EMA 16", "value": "ema_8_16"},
    {"label": "EMA WC(HLCC/4) 4x8", "value": "ema_wc_4_8"},
]

DEFAULT_FILTER_OPTIONS: list[dict[str, str]] = [
    {"label": "EMA 75", "value": "ema_75"},
    {"label": "RSI 15", "value": "rsi_15"},
    {"label": "Stochastic 5/3/3", "value": "stochastic_5_3_3"},
    {"label": "Stochastic 7/5/3", "value": "stochastic_7_5_3"},
    {"label": "MACD 4/5/3", "value": "macd_4_5_3"},
    {"label": "Bollinger 20/2", "value": "bollinger_20_2"},
]


def normalize_option_label(text: str) -> str:
    return text.removeprefix("✓ ").strip()


def find_tick_value(label: str) -> int | None:
    for item in DEFAULT_TICK_OPTIONS:
        if item["label"] == label:
            return item["value"]

    return None


def summarize_signal_keys(enabled: Iterable[str]) -> str:
    labels: list[str] = []
    enabled_set = set(enabled)

    for item in DEFAULT_SIGNAL_OPTIONS:
        if item["value"] in enabled_set:
            labels.append(item["label"])

    return ", ".join(labels) if labels else "ничего не выбрано"


def summarize_filter_keys(enabled: Iterable[str]) -> str:
    labels: list[str] = []
    enabled_set = set(enabled)

    for item in DEFAULT_FILTER_OPTIONS:
        if item["value"] in enabled_set:
            labels.append(item["label"])

    return ", ".join(labels) if labels else "не выбраны"
