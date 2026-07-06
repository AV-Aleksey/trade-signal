from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

from internal.telegram import options

KB_RESTART = "⬅️ Назад"
KB_STOP = "⏹️ Остановить"
KB_AI = "🤖 Анализ ИИ"
KB_REQUEST_DATA = "📊 Запросить данные"
KB_SIGNAL_SELECT_ALL = "☑️ Выбрать все"
KB_SIGNAL_DONE = "✅ Готово"
KB_PRESET_ADD = "➕ Добавить сигнал"
KB_PRESET_DONE = "✅ Готово (мониторинг)"


def monitoring_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=KB_STOP)],
        [KeyboardButton(text=KB_AI), KeyboardButton(text=KB_REQUEST_DATA)],
    ]

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def pair_keyboard() -> ReplyKeyboardMarkup:
    pair_rows = [[KeyboardButton(text=pair)] for pair in options.DEFAULT_PICK_PAIRS]

    return ReplyKeyboardMarkup(
        pair_rows,
        resize_keyboard=True,
        input_field_placeholder="GB/EURUSD или кнопка ниже",
    )


def tick_keyboard() -> ReplyKeyboardMarkup:
    tick_cols = 3
    tick_rows: list[list[KeyboardButton]] = []
    row_buf: list[KeyboardButton] = []

    for item in options.DEFAULT_TICK_OPTIONS:
        row_buf.append(KeyboardButton(text=item["label"]))

        if len(row_buf) == tick_cols:
            tick_rows.append(row_buf)
            row_buf = []

    if row_buf:
        tick_rows.append(row_buf)

    tick_rows.append([KeyboardButton(text=KB_RESTART)])

    return ReplyKeyboardMarkup(
        tick_rows,
        resize_keyboard=True,
        input_field_placeholder="например: 1 минута",
    )


def token_input_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text=KB_RESTART)]],
        resize_keyboard=True,
        input_field_placeholder="Вставьте iTick токен",
    )


def _chunk_buttons(items: list[dict[str, str]], selected: set[str]) -> list[list[KeyboardButton]]:
    chunk_size = 3
    rows: list[list[KeyboardButton]] = []
    row: list[KeyboardButton] = []

    for item in items:
        value = item["value"]
        label = item["label"]
        prefix = "✓ " if value in selected else ""
        row.append(KeyboardButton(text=prefix + label))

        if len(row) == chunk_size:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return rows


def signal_selection_keyboard(selected: set[str]) -> ReplyKeyboardMarkup:
    rows = _chunk_buttons(options.DEFAULT_SIGNAL_OPTIONS, selected)

    rows.append(
        [
            KeyboardButton(text=KB_SIGNAL_SELECT_ALL),
            KeyboardButton(text=KB_SIGNAL_DONE),
        ],
    )
    rows.append([KeyboardButton(text=KB_RESTART)])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def filter_selection_keyboard(selected: set[str]) -> ReplyKeyboardMarkup:
    rows = _chunk_buttons(options.DEFAULT_FILTER_OPTIONS, selected)

    rows.append(
        [
            KeyboardButton(text=KB_SIGNAL_SELECT_ALL),
            KeyboardButton(text=KB_SIGNAL_DONE),
        ],
    )
    rows.append([KeyboardButton(text=KB_RESTART)])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def preset_selection_keyboard(
    presets: list[dict],
    selected_ids: set[int],
) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    for preset in presets:
        pid = int(preset["id"])
        name = str(preset["name"])
        k_type = preset["k_type"]
        mark = "✓ " if pid in selected_ids else "◻ "
        rows.append([KeyboardButton(text=f"{mark}{name} (TF {k_type})")])

    rows.append(
        [
            KeyboardButton(text=KB_PRESET_DONE),
        ]
    )
    rows.append([KeyboardButton(text=KB_RESTART)])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def preset_manage_keyboard(
    presets: list[dict],
) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    for preset in presets:
        name = str(preset["name"])
        k_type = preset["k_type"]
        rows.append([KeyboardButton(text=f"{name} (TF {k_type})")])
        rows.append([KeyboardButton(text=f"🗑 {name}")])

    rows.append([KeyboardButton(text=KB_PRESET_ADD)])
    rows.append([KeyboardButton(text=KB_RESTART)])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
