# ТЗ / описание проекта (актуально под репозиторий)

Текст оптимизирован для LLM: структура, типы, форматы, последовательность действий.

---

### Торговый сигнальный модуль (Python)

#### Общая цель
Скрипт подключается к Forex API **iTick**, загружает свечи (Kline), считает индикаторы (`pandas_ta`) и определяет бычье пересечение короткой EMA и длинной EMA на двух последних закрытых барах. Опционально — Telegram-бот поверх той же логики.

#### Стек и модули

| Модуль | Назначение |
|--------|------------|
| `internal/config.py` | Настройки из `.env` через `pydantic-settings` |
| `internal/itick.py` | Класс `Itick`: HTTP-клиент iTick, форматирование свечей, индикаторы, сигнал, опционально график |
| `internal/main.py` | Точка входа CLI: `connect` → свечи → DataFrame → индикаторы → сигнал |
| `internal/telegram_bot.py` | Бот: ввод пары `XXXXXX`, вызов `main`, вывод сигнала и превью DataFrame |

Разбиение не полностью совпадает с «чистой архитектурой» из старого ТЗ: логика API и индикаторов сосредоточена в `Itick`.

---

#### 1. Конфигурация (`.env`)

Парсинг: `BaseSettings` в `config.py`, файл `.env` в корне проекта (или переменные окружения).

**Переменные:**

| Переменная | Описание |
|------------|----------|
| `ITICK_API_KEY` | Токен iTick (заголовок `token`) |
| `ITICK_ENVIRONMENT` | `DEV` или `PROD` — выбор базового URL |
| `BOT_API_KEY` | Токен Telegram-бота (для `telegram_bot.py`) |
| `LOG_LEVEL` | По умолчанию `INFO` |

**Пример `.env`:**

```
ITICK_API_KEY=your_itick_token
ITICK_ENVIRONMENT=DEV
BOT_API_KEY=your_telegram_bot_token
LOG_LEVEL=INFO
```

---

#### 2. Клиент iTick и «подключение»

- Базовые URL: `DEV` → `https://api-free.itick.org/forex`, `PROD` → `https://api0.itick.org/forex`.
- `Itick.connect()` только выставляет флаг; реальная проверка — успешный HTTP-запрос к `/kline`.
- Запрос: `GET {base}/kline` с query `region`, `code`, `kType`, `limit`, заголовки `accept: application/json`, `token: <ITICK_API_KEY>`.
- Ответ JSON: ожидается `code == 0`, массив свечей в `data`. Иначе — исключение.

---

#### 3. Загрузка свечей

**Параметры по умолчанию в `main`:**

| Параметр | Значение |
|----------|----------|
| Регион | `GB` (`DEFAULT_ITICK_REGION`) |
| Инструмент | `GBPJPY` (`DEFAULT_ITICK_CODE`), в боте переопределяется вводом пользователя |
| Интервал (`kType`) | `1` — **1 минута** (`DEFAULT_ITICK_K_TYPE`) |
| Лимит свечей | `500` |

Сопоставление `kType` → длительность бара (мс) задано в `KTYPE_TO_MILLISECONDS` в `itick.py` (1 → 60 000 мс и т.д.).

---

#### 4. Формат сырых свечей и DataFrame

Элемент `data[]` — словарь; фактические ключи iTick (не абстрактный брокер):

- Время открытия бара: `t` — **Unix ms**.
- OHLC: `o`, `h`, `l`, `c` (числа).
- Объём: `v` (опционально; по умолчанию `0`).

**Закрытый бар:** не поле `complete`, а проверка по времени: текущее UTC-время ≥ `t + interval_ms` для данного `kType` (`is_candle_closed`).

Итоговый `pandas.DataFrame`:

- `time` — `datetime64[ns, UTC]` из `t` (`unit="ms"`).
- `open`, `high`, `low`, `close` — `float`.
- `volume` — `float` из `v`.

Если после фильтра закрытых баров список пуст — `RuntimeError`.

---

#### 5. Визуализация

В коде есть `Itick.plot_close(df)` — `plt.plot(df["close"])` и `plt.show()`. Из `main()` по умолчанию **не вызывается**; можно вызвать вручную для отладки.

---

#### 6. Индикаторы (`calculate_indicators`)

Библиотека: `pandas_ta as ta`.

Колонки:

- `EMA_4` = `ta.ema(df["close"], length=4)`
- `EMA_8` = `ta.ema(df["close"], length=8)`
- `ATR_14` = `ta.atr(high, low, close, length=14)`

Первые строки могут содержать NaN — при проверке сигнала строки без обеих EMA отбрасываются (`dropna` по `EMA_4`, `EMA_8`).

---

#### 7. Сигнал (`check_signal` / логика кроссовера)

Не отдельная функция `ema_crossover` в глобальной области — метод `Itick.check_signal(df)`.

- Берутся **две последние** строки после `dropna` по `EMA_4` и `EMA_8`.
- **Buy:**  
  `last["EMA_4"] > last["EMA_8"]` **и** `prev["EMA_4"] < prev["EMA_8"]`  
  (EMA 4 снизу вверх пересекает EMA 8).

Текст при сигнале: **«EMA 4 пересекает EMA 8»** (`main.py`, константа в `telegram_bot.py`).

Коэффициент `tp_ratio = 1.5` из старого ТЗ **не используется**.

---

#### 8. CLI (`python -m internal.main` или запуск `internal/main.py`)

Последовательность: `Itick()` → `connect()` → `fetch_candles` → `format_candles` → `calculate_indicators` → `check_signal` → словарь:

```python
{
    "signal": str,
    "indicator": str,
    "interval": "1m",
    "data_frame": pd.DataFrame,
}
```

Печать в консоль при прямом запуске — только возвращаемый объект через `print(main(...))`.

---

#### 9. Telegram-бот

Запуск: модуль `internal.telegram_bot` (`main()` → polling).

- Команда / кнопка Start → запрос **6 букв** пары (например `GBPJPY`). Условное полное обозначение `GB/GBPJPY` см. в BOT.md.
- Вызов `run_signal_main(client=Itick(), code=...)`.
- Сообщения: параметры, сигнал (иконка при совпадении с константой `BUY_SIGNAL_TEXT`), превью DataFrame по колонкам EMA, кнопка «Показать DataFrame».

---

#### Примечания для LLM

- Ключи ответа API — **iTick Kline** (`t`, `o`, `h`, `l`, `c`, `v`), не абстрактный `ask`/`complete`.
- Индикаторы в коде: **EMA(4)** и **EMA(8)**, не EMA(5)/EMA(8).
- Таймфрейм по умолчанию: **1m**, не M15.
- Обрабатывать сетевые ошибки (`requests`), код ответа API `code != 0`, пустые данные после фильтрации.
