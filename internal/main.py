import pandas as pd

from internal.answer import MainAnalysisResult
from internal.itick import Itick

DEFAULT_ITICK_CODE: str = "GB/GBPJPY"
DEFAULT_ITICK_K_TYPE: int = 1


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
    ema_cross = client.check_signal(df=indicators_frame)

    signals: list[dict[str, bool]] = []

    if ema_cross["is_ema_crossing"]:
        signals.append(ema_cross)

    print(indicators_frame)

    return {
        "indicator": code,
        "signals": signals,
        "ema_last_two_rows": client.extract_last_two_ema_rows(indicators_frame),
        "data_frame": indicators_frame,
    }


if __name__ == "__main__":
    main()
