from internal.itick import Itick
import pandas as pd

DEFAULT_ITICK_CODE: str = "GB/GBPJPY"
DEFAULT_ITICK_K_TYPE: int = 1

def main(
    code: str = DEFAULT_ITICK_CODE,
    k_type: int = DEFAULT_ITICK_K_TYPE,
    client: Itick | None = None,
) -> dict[str, str | pd.DataFrame]:
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
    has_buy_signal = client.check_signal(df=indicators_frame)

    signal_text = "EMA 4 пересекает EMA 8" if has_buy_signal else "Нет сигнала"

    return {
        "indicator": code,
        "signal": signal_text,
        "data_frame": indicators_frame,
    }


if __name__ == "__main__":
    main()
