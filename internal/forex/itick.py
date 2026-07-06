from __future__ import annotations

from datetime import datetime, timezone

import matplotlib.pyplot as plt
import pandas as pd
import pandas_ta as ta
import requests

from internal.config import settings
from internal.forex.filter import FilterChecker, FilterFlags, FilterName
from internal.forex.signal import SignalChecker, Signals
from internal.storage.itick_token_repository import ItickTokenRepository

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

WARMUP_LIMIT = 1


class ItickUnavailableError(RuntimeError):
    def __init__(self, reason: str | None = None) -> None:
        self.reason: str = reason or "unknown"

        super().__init__("Сервис временно недоступен, возможно просрочен токен")


class MissingItickTokenError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Не найден iTick токен. Используй /itick для сохранения токена.")


class Itick:
    def __init__(
        self,
        telegram_user_id: int | None = None,
        token: str | None = None,
        signal_checker: SignalChecker | None = None,
        filter_checker: FilterChecker | None = None,
    ) -> None:
        environment: str = settings.ITICK_ENVIRONMENT.strip().upper()
        base_url: str = ITICK_FOREX_BASE_URLS.get(environment)

        print("Запросы будут отправляться на URL: ", base_url)

        self._base_url: str = base_url.rstrip("/")
        resolved_token = (token or "").strip()

        if not resolved_token and telegram_user_id is not None:
            resolved_token = (
                ItickTokenRepository().get_itick_token(telegram_user_id) or ""
            ).strip()

        if not resolved_token:
            resolved_token = settings.ITICK_API_KEY.strip()

        if not resolved_token:
            raise MissingItickTokenError()

        self._token: str = resolved_token
        self._is_connected: bool = False
        self._signal_checker: SignalChecker = (
            signal_checker if signal_checker is not None else SignalChecker()
        )
        self._filter_checker: FilterChecker = (
            filter_checker if filter_checker is not None else FilterChecker()
        )

    def connect(
        self,
        region: str,
        code: str,
        k_type: int,
    ) -> None:
        self._request_kline(
            region=region,
            code=code,
            k_type=k_type,
            limit=WARMUP_LIMIT,
        )

        self._is_connected = True

    def fetch_candles(
        self,
        region: str,
        code: str,
        k_type: int,
    ) -> list[dict[str, float | int]]:
        if not self._is_connected:
            raise RuntimeError("Client is not connected")

        return self._request_kline(
            region=region,
            code=code,
            k_type=k_type,
            limit=500,
        )

    def _request_kline(
        self,
        region: str,
        code: str,
        k_type: int,
        limit: int,
    ) -> list[dict[str, float | int]]:
        endpoint: str = f"{self._base_url}/kline"

        try:
            response: requests.Response = requests.get(
                endpoint,
                params={
                    "region": region,
                    "code": code,
                    "kType": k_type,
                    "limit": limit,
                },
                headers={"accept": "application/json", "token": self._token},
                timeout=45.0,
            )
        except requests.RequestException as exc:
            raise ItickUnavailableError(str(exc)) from exc

        if response.status_code == 401:
            raise ItickUnavailableError(
                f"401 Unauthorized for url: {response.url}",
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ItickUnavailableError(
                f"{response.status_code} {response.reason} for url: {response.url}",
            ) from exc

        payload = response.json()
        api_code = int(payload.get("code", -1))

        if api_code != 0:
            raise ItickUnavailableError(
                f"iTick API error: {payload.get('msg')}",
            )

        data = payload.get("data", [])

        if not isinstance(data, list):
            raise ItickUnavailableError("iTick response field 'data' is not a list")

        candles = [item for item in data if isinstance(item, dict)]

        if not candles:
            raise ItickUnavailableError("iTick returned empty candle data")

        return candles

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
        result_df["EMA_75"] = ta.ema(result_df["close"], length=75)
        result_df["RSI_15"] = ta.rsi(result_df["close"], length=15)

        result_df["weighted_close"] = (
            result_df["high"] + result_df["low"] + result_df["close"] + result_df["close"]
        ) / 4
        result_df["EMA_4_WC"] = ta.ema(result_df["weighted_close"], length=4)
        result_df["EMA_8_WC"] = ta.ema(result_df["weighted_close"], length=8)

        # 2. Осцилляторы
        stoch_5_3_3 = ta.stoch(
            high=result_df["high"],
            low=result_df["low"],
            close=result_df["close"],
            k=5,
            d=3,
            smooth_k=3,
        )
        stoch_7_5_3 = ta.stoch(
            high=result_df["high"],
            low=result_df["low"],
            close=result_df["close"],
            k=7,
            d=5,
            smooth_k=3,
        )
        result_df["STOCHk_5_3_3"] = stoch_5_3_3["STOCHk_5_3_3"]
        result_df["STOCHk_7_5_3"] = stoch_7_5_3["STOCHk_7_5_3"]

        macd = ta.macd(result_df["close"], fast=4, slow=5, signal=3)
        result_df["MACDh_4_5_3"] = macd["MACDh_4_5_3"]

        bbands = ta.bbands(result_df["close"], length=20, std=2)
        bbm_series = None

        if "BBM_20_2.0" in bbands.columns:
            bbm_series = bbands["BBM_20_2.0"]
        elif "BBM_20_2" in bbands.columns:
            bbm_series = bbands["BBM_20_2"]
        elif bbands.shape[1] >= 2:
            bbm_series = bbands.iloc[:, 1]

        result_df["BBM_20_2.0"] = bbm_series

        return result_df

    def check_all(self, df: pd.DataFrame) -> Signals:
        return self._signal_checker.check_all(df)

    def check_filters(
        self,
        df: pd.DataFrame,
        filters: list[FilterName] | None = None,
    ) -> dict[FilterName, FilterFlags]:
        return self._filter_checker.check(df, filters)

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

            if pd.notna(row.get("EMA_4_WC")):
                item["EMA_4_WC"] = float(row["EMA_4_WC"])

            if pd.notna(row.get("EMA_8_WC")):
                item["EMA_8_WC"] = float(row["EMA_8_WC"])

            if pd.notna(row.get("close")):
                item["close"] = float(row["close"])

            result.append(item)

        return result

    def plot_close(self, df: pd.DataFrame):
        # Рисуем график закрытия.
        plt.plot(df["close"])
        plt.show()
