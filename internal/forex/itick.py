from __future__ import annotations

from datetime import datetime, timezone

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from internal.config import settings
from internal.forex.signal import SignalChecker, Signals

# Базовые параметры запроса к iTick.
ITICK_FOREX_BASE_URLS = {
    "DEV": "https://api-free.itick.org/forex",
    "PROD": "https://api0.itick.org/forex",
}

# kType → длительность бара (мс) для is_candle_closed.
# Источник: https://docs.itick.org/en/rest-api/forex/forex-kline
# 1=1м, 2=5м, 3=15м, 4=30м, 5=1ч, 6=2ч, 7=4ч, 8=день, 9=неделя, 10=месяц (~30 суток).
KTYPE_TO_MILLISECONDS: dict[int, int] = {
    1: 60_000,
    2: 300_000,
    3: 900_000,
    4: 1_800_000,
    5: 3_600_000,
    6: 7_200_000,
    7: 14_400_000,
    8: 86_400_000,
    9: 604_800_000,
}


class Itick:
    def __init__(self, signal_checker: SignalChecker | None = None) -> None:
        environment: str = settings.ITICK_ENVIRONMENT.strip().upper()
        base_url: str = ITICK_FOREX_BASE_URLS.get(environment)

        print("Запросы будут отправляться на URL: ", base_url)

        self._base_url: str = base_url.rstrip("/")
        self._token: str = settings.ITICK_API_KEY
        self._is_connected: bool = False
        self._signal_checker: SignalChecker = (
            signal_checker if signal_checker is not None else SignalChecker()
        )

    def connect(self) -> None:
        self._is_connected = True

    def fetch_candles(
        self,
        region: str,
        code: str,
        k_type: int,
    ) -> list[dict[str, float | int]]:
        # Запрашиваем сырые Kline-данные.
        if not self._is_connected:
            raise RuntimeError("Client is not connected")

        endpoint: str = f"{self._base_url}/kline"

        response: requests.Response = requests.get(
            endpoint,
            params={
                "region": region,
                "code": code,
                "kType": k_type,
                "limit": 500,
            },
            headers={"accept": "application/json", "token": self._token},
            timeout=45.0,
        )

        response.raise_for_status()
        payload = response.json()

        api_code = int(payload.get("code", -1))

        if api_code != 0:
            raise RuntimeError(f"iTick API error: {payload.get('msg')}")

        data = payload.get("data", [])

        if not isinstance(data, list):
            raise RuntimeError("iTick response field 'data' is not a list")

        return [item for item in data if isinstance(item, dict)]

    def is_candle_closed(self, candle_open_time_ms: int, k_type: int) -> bool:
        # Проверяем, что бар уже завершился.
        interval_ms: int | None = KTYPE_TO_MILLISECONDS.get(k_type)

        if interval_ms is None:
            raise ValueError(f"Unsupported kType: {k_type}")

        now_ms: int = int(datetime.now(tz=timezone.utc).timestamp() * 1000)

        return now_ms >= candle_open_time_ms + interval_ms

    def format_candles(
        self,
        candles: list[dict[str, float | int]],
        k_type: int,
    ) -> pd.DataFrame:
        # Фильтруем закрытые бары и собираем DataFrame.
        closed_candles: list[dict[str, float | int]] = []

        for item in candles:
            time_ms: int = int(item.get("t", 0))

            if time_ms == 0:
                continue

            if not self.is_candle_closed(candle_open_time_ms=time_ms, k_type=k_type):
                continue

            closed_candles.append(item)

        if not closed_candles:
            raise RuntimeError("No closed candles available after filtering")

        frame: pd.DataFrame = pd.DataFrame(
            {
                "time": pd.to_datetime(
                    [int(item["t"]) for item in closed_candles],
                    unit="ms",
                    utc=True,
                ),
                "open": [float(item["o"]) for item in closed_candles],
                "high": [float(item["h"]) for item in closed_candles],
                "low": [float(item["l"]) for item in closed_candles],
                "close": [float(item["c"]) for item in closed_candles],
                "volume": [float(item.get("v", 0.0)) for item in closed_candles],
            }
        )

        return frame

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        result_df: pd.DataFrame = df.copy()
        # 1. Трендовые
        result_df["EMA_4"] = ta.ema(result_df["close"], length=4)
        result_df["EMA_8"] = ta.ema(result_df["close"], length=8)
        result_df["EMA_16"] = ta.ema(result_df["close"], length=16)

        macd = ta.macd(result_df["close"])

        if macd is not None and not macd.empty:
            result_df = pd.concat([result_df, macd], axis=1)

        return result_df

    def check_all(self, df: pd.DataFrame) -> Signals:
        return self._signal_checker.check_all(df)

    def extract_fresh_candles(self, df: pd.DataFrame):
        clean = df.dropna(subset=["EMA_4", "EMA_8"])

        if len(clean) < 2:
            return None

        result: list[dict[str, float | str]] = []

        for _, row in clean.iloc[-2:].iterrows():
            t = pd.Timestamp(row["time"])

            if t.tzinfo is None:
                t = t.tz_localize("UTC")
            else:
                t = t.tz_convert("UTC")

            time_str = t.strftime("%Y-%m-%d %H:%M UTC")
            item: dict[str, float | str] = {
                "time": time_str,
                "EMA_4": float(row["EMA_4"]),
                "EMA_8": float(row["EMA_8"]),
            }

            if pd.notna(row.get("EMA_16")):
                item["EMA_16"] = float(row["EMA_16"])

            if pd.notna(row.get("close")):
                item["close"] = float(row["close"])

            result.append(item)

        return result

    def plot_close(self, df: pd.DataFrame):
        # Рисуем график закрытия.
        plt.plot(df["close"])
        plt.show()
