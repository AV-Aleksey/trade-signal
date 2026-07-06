START_PAIR_PROMPT = "Выберите валютную пару кнопкой или введите вручную в формате forex GB/XXXXXX"
ITICK_TOKEN_PROMPT = "Отправьте iTick токен одним сообщением."
ITICK_TOKEN_SAVED = "Токен iTick сохранён."
ITICK_TOKEN_REQUIRED = "Сначала добавьте iTick токен через команду /itick."
SELECT_TICK_PROMPT = "Выберите таймфрейм кнопкой"
INVALID_TICK_PROMPT = "Выберите таймфрейм кнопкой."
PRESET_MENU_TITLE = "Ваши сигнальные пресеты (макс 3):"
PRESET_EMPTY = "Пока нет пресетов. Создайте новый."
PRESET_LIMIT = "Достигнут лимит пресетов (3). Удалите один, чтобы добавить новый."
PRESET_ENTER_NAME = "Введите имя пресета."
PRESET_NAME_EMPTY = "Имя не может быть пустым."
PRESET_NEED_SIGNAL = "Выберите хотя бы один сигнал."
PRESET_SAVED = "Пресет сохранён."
PRESET_DELETED = "Пресет удалён."
PRESET_SELECT_FOR_MONITOR = "Выберите пресеты для мониторинга (✓ — выбрано)."
PRESET_NEED_SELECT = "Нужно выбрать хотя бы один пресет."
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
