from collections.abc import Sequence
from typing import TypedDict

import pandas as pd

from internal.forex.filter import FilterFlags, FilterName
from internal.forex.itick import Itick
from internal.forex.signal import Signals


DEFAULT_ITICK_CODE: str = "GB/GBPJPY"
DEFAULT_ITICK_K_TYPE: int = 1

class MainAnalysisResult(TypedDict):
    indicator: str
    signals: Signals
    filters: dict[FilterName, FilterFlags]
    data_frame: pd.DataFrame
    fresh_candles: list[dict[str, float | int | str]] | None

def main(
    code: str = DEFAULT_ITICK_CODE,
    k_type: int = DEFAULT_ITICK_K_TYPE,
    enabled_filter_keys: Sequence[FilterName] | None = None,
    telegram_user_id: int | None = None,
    client: Itick | None = None,
) -> MainAnalysisResult:
    if client is None:
        client = Itick(telegram_user_id=telegram_user_id)

    region, code_name = code.split('/')

    client.connect(region=region, code=code_name, k_type=k_type)

    candles = client.fetch_candles(
        code=code_name,
        region=region,
        k_type=k_type,
    )

    candles_frame = client.format_candles(candles=candles, k_type=k_type)
    indicators_frame = client.calculate_indicators(df=candles_frame)
    signal_map = client.check_all(df=indicators_frame)
    filter_map = client.check_filters(df=indicators_frame, filters=enabled_filter_keys)
    fresh_candles = client.extract_fresh_candles(indicators_frame)

    print(indicators_frame)

    return {
        "indicator": code,
        "signals": signal_map,
        "filters": filter_map,
        "fresh_candles": fresh_candles,
        "data_frame": indicators_frame,
    }


if __name__ == "__main__":
    main()
