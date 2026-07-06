from telegram import BotCommand, MenuButtonCommands
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from internal.config import settings
from internal.storage.itick_token_repository import ItickTokenRepository
from internal.storage.preset_repository import UserSignalPresetRepository
from internal.telegram.services import AiReportService, DataSnapshotService
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import (
    INPUT_ITICK_TOKEN,
    PRESET_CREATE_FILTERS,
    PRESET_CREATE_NAME,
    PRESET_CREATE_SIGNALS,
    PRESET_CREATE_TICK,
    SELECT_PRESETS,
    MONITORING,
    SELECT_PAIR,
    TEXT_MESSAGE_FILTER,
)
from internal.telegram.steps.monitoring_step import make_monitoring_handler
from internal.telegram.steps.pair_step import make_pair_handler
from internal.telegram.steps.start_step import make_start_handler
from internal.telegram.steps.token_step import make_itick_entry_handler, make_token_handler
from internal.telegram.steps.presets_step import (
    make_signals_entry_handler,
    make_preset_menu_handler,
    make_preset_create_name_handler,
    make_preset_create_tick_handler,
    make_preset_create_signals_handler,
    make_preset_create_filters_handler,
)


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("itick", "Сохранить iTick токен"),
            BotCommand("signals", "Настроить сигналы"),
        ],
    )
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def build_application(
    default_filter_keys: frozenset[str] | None = None,
) -> Application:
    token = settings.BOT_API_KEY.strip()

    if not token:
        raise RuntimeError("Не задан BOT_API_KEY")

    filters_enabled = default_filter_keys is None
    default_filter_keys = default_filter_keys or frozenset()

    state_store = SessionStateStore()
    itick_token_repository = ItickTokenRepository()
    preset_repository = UserSignalPresetRepository()
    ai_service = AiReportService(settings.OPEN_ROUTER_API_KEY)
    snapshot_service = DataSnapshotService()

    start_handler = make_start_handler(state_store)
    pair_handler = make_pair_handler(state_store, preset_repository)
    itick_entry_handler = make_itick_entry_handler()
    token_handler = make_token_handler(itick_token_repository)
    preset_menu_handler = make_preset_menu_handler(state_store, preset_repository)
    preset_manage_entry = make_signals_entry_handler(state_store, preset_repository)
    preset_create_name_handler = make_preset_create_name_handler(state_store, preset_repository)
    preset_create_tick_handler = make_preset_create_tick_handler(state_store)
    preset_create_signals_handler = make_preset_create_signals_handler(state_store)
    preset_create_filters_handler = make_preset_create_filters_handler(state_store, preset_repository)
    monitoring_handler = make_monitoring_handler(
        state_store,
        start_handler,
        ai_service,
        snapshot_service,
        preset_repository,
    )

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler(
                "start",
                start_handler,
            ),
            CommandHandler(
                "signals",
                preset_manage_entry,
            ),
            CommandHandler(
                "itick",
                itick_entry_handler,
            ),
        ],
        states={
            SELECT_PAIR: [
                MessageHandler(TEXT_MESSAGE_FILTER, pair_handler),
            ],
            INPUT_ITICK_TOKEN: [
                MessageHandler(TEXT_MESSAGE_FILTER, token_handler),
            ],
            SELECT_PRESETS: [
                MessageHandler(TEXT_MESSAGE_FILTER, preset_menu_handler),
            ],
            PRESET_CREATE_NAME: [
                MessageHandler(TEXT_MESSAGE_FILTER, preset_create_name_handler),
            ],
            PRESET_CREATE_TICK: [
                MessageHandler(TEXT_MESSAGE_FILTER, preset_create_tick_handler),
            ],
            PRESET_CREATE_SIGNALS: [
                MessageHandler(TEXT_MESSAGE_FILTER, preset_create_signals_handler),
            ],
            PRESET_CREATE_FILTERS: [
                MessageHandler(TEXT_MESSAGE_FILTER, preset_create_filters_handler),
            ],
            MONITORING: [
                MessageHandler(TEXT_MESSAGE_FILTER, monitoring_handler),
            ],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    application = (
        Application.builder()
        .token(token)
        .concurrent_updates(False)
        .post_init(_post_init)
        .build()
    )
    application.add_handler(conversation)

    return application
