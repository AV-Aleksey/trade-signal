START_PAIR_PROMPT = "Выберите валютную пару кнопкой или введите вручную в формате forex GB/XXXXXX"
ITICK_TOKEN_PROMPT = "Отправьте iTick токен одним сообщением."
ITICK_TOKEN_SAVED = "Токен iTick сохранён."
ITICK_TOKEN_REQUIRED = "Сначала добавьте iTick токен через команду /itick."
SELECT_TICK_PROMPT = "Выберите таймфрейм кнопкой"
INVALID_TICK_PROMPT = "Выберите таймфрейм кнопкой."
SELECT_SIGNAL_PROMPT = (
    "Выберите сигналы для уведомлений (минимум один): строка — вкл/выкл, "
    "«{select_all}» или «{done}»."
)
SIGNAL_NEED_AT_LEAST_ONE = "Нужно выбрать хотя бы один сигнал (или «{select_all}»)."
SIGNAL_BUTTONS_ONLY = (
    "Используйте кнопки: сигнал, «{select_all}», "
    "«{done}», «{restart}»."
)
SELECT_FILTER_PROMPT = (
    "Выберите фильтры для уведомлений: строка — вкл/выкл, "
    "«{select_all}» или «{done}». Можно оставить без фильтров."
)
FILTER_BUTTONS_ONLY = (
    "Используйте кнопки: фильтр, «{select_all}», "
    "«{done}», «{restart}»."
)
NEED_PAIR_FIRST = "Сначала выберите пару."
NEED_PAIR_AND_TICK = "Сначала выберите пару и таймфрейм."
ONLY_MONITOR_BUTTONS = "Только кнопки: {stop}, {ai}, {request_data}."
OPEN_ROUTER_MISSING = "Не задан OPEN_ROUTER_API_KEY (open_router в .env)."
AI_COOLDOWN_WAIT = "Отчет формируется. Подожди ещё ~{seconds} с."
AI_IN_PROGRESS = (
    "ИИ: отчет формируется. \n"
    "Повторный ИИ — не раньше чем через {cooldown} с."
)
SCRIPT_FAILED = "Script execution failed: {error}"
