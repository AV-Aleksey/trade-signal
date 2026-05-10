from __future__ import annotations

from datetime import datetime, timezone

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from internal.config import settings

# Базовые параметры запроса к iTick.
ITICK_FOREX_BASE_URLS = {
    "DEV": "https://api-free.itick.org/forex",
    "PROD": "https://api0.itick.org/forex",
}

# Карта интервалов kType в миллисекундах для проверки закрытия бара.
KTYPE_TO_MILLISECONDS = {
    1: 60_000,
    2: 900_000,
    3: 1_800_000,
}

class Itick:
    # Инкапсулируем все этапы ТЗ в одном классе.
    def __init__(self) -> None:
        environment: str = settings.ITICK_ENVIRONMENT.strip().upper()
        base_url: str = ITICK_FOREX_BASE_URLS.get(environment)

        print("Запросы будут отправляться на URL: ", base_url)

        self._base_url: str = base_url.rstrip("/")
        self._token: str = settings.ITICK_API_KEY
        self._is_connected: bool = False

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
            timeout=30.0,
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
        # Добавляем EMA и ATR.
        result_df: pd.DataFrame = df.copy()

        result_df["EMA_4"] = ta.ema(result_df["close"], length=4)
        result_df["EMA_8"] = ta.ema(result_df["close"], length=8)
        
        result_df["ATR_14"] = ta.atr(
            result_df["high"],
            result_df["low"],
            result_df["close"],
            length=14,
        )

        return result_df

    def check_signal(self, df: pd.DataFrame) -> bool:
        # Проверяем пересечение EMA на двух последних барах.
        clean_df = df.dropna(subset=["EMA_4", "EMA_8"]).copy()

        if len(clean_df) < 2:
            return False

        last_candle = clean_df.iloc[-1]
        previous_candle = clean_df.iloc[-2]

        has_buy_signal = (last_candle["EMA_4"] > last_candle["EMA_8"]) and (
            previous_candle["EMA_4"] < previous_candle["EMA_8"]
        )

        return has_buy_signal

    def plot_close(self, df: pd.DataFrame) -> None:
        # Рисуем график закрытия.
        plt.plot(df["close"])
        plt.show()
