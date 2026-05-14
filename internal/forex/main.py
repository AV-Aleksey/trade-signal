from typing import TypedDict

import pandas as pd

from internal.forex.itick import Itick
from internal.forex.signal import Signals



DEFAULT_ITICK_CODE: str = "GB/GBPJPY"
DEFAULT_ITICK_K_TYPE: int = 1

class MainAnalysisResult(TypedDict):
    indicator: str
    signals: Signals
    data_frame: pd.DataFrame
    fresh_candles: list[dict[str, float | int | str]] | None

def main(
    code: str = DEFAULT_ITICK_CODE,
    k_type: int = DEFAULT_ITICK_K_TYPE,
    client: Itick | None = None,
) -> MainAnalysisResult:
    if client is None:
        client = Itick()

    client.connect()

    region, code_name = code.split('/')

    candles = client.fetch_candles(
        code=code_name,
        region=region,
        k_type=k_type,
    )

    candles_frame = client.format_candles(candles=candles, k_type=k_type)
    indicators_frame = client.calculate_indicators(df=candles_frame)
    signal_map = client.check_all(df=indicators_frame)
    fresh_candles = client.extract_fresh_candles(indicators_frame)

    print(indicators_frame)

    return {
        "indicator": code,
        "signals": signal_map,
        "fresh_candles": fresh_candles,
        "data_frame": indicators_frame,
    }


if __name__ == "__main__":
    main()
