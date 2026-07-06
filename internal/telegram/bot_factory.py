from telegram import BotCommand, MenuButtonCommands
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)

from internal.config import settings
from internal.storage.itick_token_repository import ItickTokenRepository
from internal.telegram.services import AiReportService, DataSnapshotService
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import (
    INPUT_ITICK_TOKEN,
    MONITORING,
    SELECT_FILTERS,
    SELECT_PAIR,
    SELECT_SIGNALS,
    SELECT_TICK,
    TEXT_MESSAGE_FILTER,
)
from internal.telegram.steps.filters_step import make_filters_handler
from internal.telegram.steps.monitoring_step import make_monitoring_handler
from internal.telegram.steps.pair_step import make_pair_handler
from internal.telegram.steps.signals_step import make_signals_handler
from internal.telegram.steps.start_step import make_start_handler
from internal.telegram.steps.tick_step import make_tick_handler
from internal.telegram.steps.token_step import make_itick_entry_handler, make_token_handler


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("itick", "Сохранить iTick токен"),
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
    ai_service = AiReportService(settings.OPEN_ROUTER_API_KEY)
    snapshot_service = DataSnapshotService()

    start_handler = make_start_handler(state_store)
    pair_handler = make_pair_handler(state_store)
    itick_entry_handler = make_itick_entry_handler()
    token_handler = make_token_handler(itick_token_repository)
    tick_handler = make_tick_handler(state_store, start_handler)
    signals_handler = make_signals_handler(
        state_store,
        start_handler,
        filters_enabled,
        default_filter_keys,
    )
    filters_handler = make_filters_handler(
        state_store,
        start_handler,
    )
    monitoring_handler = make_monitoring_handler(
        state_store,
        start_handler,
        ai_service,
        snapshot_service,
    )

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler(
                "start",
                start_handler,
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
            SELECT_TICK: [
                MessageHandler(TEXT_MESSAGE_FILTER, tick_handler),
            ],
            SELECT_SIGNALS: [
                MessageHandler(TEXT_MESSAGE_FILTER, signals_handler),
            ],
            SELECT_FILTERS: [
                MessageHandler(TEXT_MESSAGE_FILTER, filters_handler),
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
