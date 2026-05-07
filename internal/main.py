from internal.itick import Itick

ITICK_REGION: str = "GB"
ITICK_CODE: str = "EURUSD"
ITICK_K_TYPE: int = 3
ITICK_LIMIT: int = 500
ITICK_TIMEOUT_SECONDS: int = 15

def main(client: Itick) -> None:
    # Выполняем этапы ТЗ строго по порядку внутри main.
    client.connect()

    candles = client.fetch_candles(
        region=ITICK_REGION,
        code=ITICK_CODE,
        k_type=ITICK_K_TYPE,
        limit=ITICK_LIMIT,
        timeout_seconds=ITICK_TIMEOUT_SECONDS,
    )

    candles_frame = client.format_candles(candles=candles, k_type=ITICK_K_TYPE)

    
    indicators_frame = client.calculate_indicators(df=candles_frame)

    print(indicators_frame)
    client.plot_close(df=indicators_frame)
    # client.generate_signal(df=indicators_frame)


if __name__ == "__main__":
    main(client=Itick())
