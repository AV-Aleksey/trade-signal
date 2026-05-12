import pandas as pd

K_TYPE_LABEL: dict[int, str] = {
    1: "1m",
    2: "15m",
    3: "30m",
}

TA_AI_TAIL_ROWS = 55

TA_SYSTEM_PROMPT = """Ты трейдер-аналитик. По приложенным OHLCV и индикаторам (EMA, ATR, RSI, MACD в CSV) напиши отчёт на русском для человека: связный текст, без таблиц и без формата KEY|VALUE.

Структура ответа (заголовки строками, далее 2–5 коротких предложений в блоке):
1) Ситуация — что делает цена последние бары (импульс, консолидация, откат).
2) Индикаторы — что показывают EMA (положение цены, пересечения/наклон), RSI (перекуп/перепрод/нейтраль), MACD (импульс, дивергенции если явно видны в хвосте), ATR (волатильность).
3) Ближайшие ориентиры — логичные зоны поддержки/сопротивления по последним локальным high/low или скользящим; укажи уровни числами из данных.
4) Сценарии — базовый (наиболее вероятный), альтернатива вверх, альтернатива вниз: куда логично смотреть цену в следующих барах на ЭТОМ таймфрейме; при каком пробое/закреплении сценарий отменяется.
5) Вывод — 2–3 предложения: общий уклон (лонг/шорт/нейтраль/ожидание), главный риск.

Пиши конкретно по цифрам из CSV, не выдумывай свечи вне выборки. Не обещай прибыль. В конце одна строка: «Не инвестиционная рекомендация.»"""


def format_dataframe_tail_csv(df: pd.DataFrame, rows: int = TA_AI_TAIL_ROWS) -> str:
    block = df.tail(rows).copy()

    if block.empty:
        return ""

    if "time" in block.columns:
        t = pd.to_datetime(block["time"], utc=True)
        block["time"] = t.dt.strftime("%Y-%m-%dT%H:%M")

    for col in block.columns:
        if col == "time":
            continue
        if pd.api.types.is_numeric_dtype(block[col]):
            block[col] = block[col].astype(float).round(6)

    return block.to_csv(index=False, na_rep="NA")


def build_ta_user_message(pair: str, k_type: int, df: pd.DataFrame) -> str:
    label = K_TYPE_LABEL.get(k_type, str(k_type))
    csv_body = format_dataframe_tail_csv(df, TA_AI_TAIL_ROWS)

    return (
        f"Инструмент: {pair}\n"
        f"Таймфрейм: {label}\n"
        f"Колонки: {','.join(df.columns.astype(str).tolist())}\n\n"
        f"Последние {TA_AI_TAIL_ROWS} закрытых баров (CSV):\n"
        f"{csv_body}\n\n"
        "Сформируй отчёт по структуре из системных инструкций. Объём текста — как краткая записка трейдеру (примерно до 1800 символов), без воды."
    )
