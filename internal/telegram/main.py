import asyncio
import time

from telegram import BotCommand, KeyboardButton, MenuButtonCommands, ReplyKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from internal.ai.main import OpenRouter, OpenRouterRateLimitError
from internal.ai.ta_ai import TA_SYSTEM_PROMPT, build_ta_user_message
from internal.config import settings
from internal.forex.main import main
from internal.telegram.answer import Answer
from internal.telegram.monitor_job import MonitorJob

KB_RESTART = "Назад"
KB_STOP = "Остановить"
KB_AI = "Анализ ИИ"
KB_REQUEST_DATA = "Запросить данные"

DEFAULT_PICK_PAIR = ["GB/USDJPY", "GB/EURUSD", "GB/XAUUSD"]
DEFAULT_TICK_VALUE = [
    {"label": "1 минута", "value": 1},
    {"label": "5 минут", "value": 2},
    {"label": "15 минут", "value": 3},
    {"label": "30 минут", "value": 4},
    {"label": "1 час", "value": 5},
    {"label": "2 часа", "value": 6},
    {"label": "4 часа", "value": 7},
    {"label": "День", "value": 8},
    {"label": "Неделя", "value": 9},
]

SELECT_PAIR, SELECT_TICK, MONITORING = range(3)

AI_COOLDOWN_SEC = 60.0


def _prepare_ai_user_message_sync(pair_code: str, k_type: int) -> str:
    result = main(code=pair_code, k_type=k_type)
    return build_ta_user_message(
        pair=pair_code,
        k_type=k_type,
        df=result["data_frame"],
    )


async def _deliver_ai_report_background(
    application: Application,
    chat_id: int,
    pair_code: str,
    k_type: int,
    api_key: str,
) -> None:
    try:
        user_block = await asyncio.to_thread(
            _prepare_ai_user_message_sync,
            pair_code,
            k_type,
        )
    except Exception as exc:
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"Данные для ИИ: {exc}",
            reply_markup=_monitoring_keyboard(),
        )

        return

    try:
        client = OpenRouter(api_key=api_key)
        reply = await asyncio.to_thread(
            client.chat,
            user_block,
            system_content=TA_SYSTEM_PROMPT,
        )

        await application.bot.send_message(
            chat_id=chat_id,
            text=reply[:4096],
            reply_markup=_monitoring_keyboard(),
        )
    except OpenRouterRateLimitError as exc:
        await application.bot.send_message(
            chat_id=chat_id,
            text=str(exc),
            reply_markup=_monitoring_keyboard(),
        )
    except Exception as exc:
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"OpenRouter: {exc}",
            reply_markup=_monitoring_keyboard(),
        )


def _monitoring_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=KB_STOP)],
        [KeyboardButton(text=KB_AI), KeyboardButton(text=KB_REQUEST_DATA)],
    ]

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def _pair_keyboard() -> ReplyKeyboardMarkup:
    pair_rows = [[KeyboardButton(text=pair)] for pair in DEFAULT_PICK_PAIR]

    return ReplyKeyboardMarkup(
        pair_rows,
        resize_keyboard=True,
        input_field_placeholder="GB/EURUSD или кнопка ниже",
    )


def _tick_keyboard() -> ReplyKeyboardMarkup:
    tick_cols = 3
    tick_rows: list[list[KeyboardButton]] = []
    row_buf: list[KeyboardButton] = []

    for item in DEFAULT_TICK_VALUE:
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


_MSG_TEXT = filters.UpdateType.MESSAGE & filters.TEXT & ~filters.COMMAND


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return ConversationHandler.END

    MonitorJob(context.job_queue, update.effective_chat.id).remove()

    context.user_data.pop("pair_code", None)
    context.user_data.pop("ai_cooldown_until", None)

    await message.reply_text(
        "Выберите валютную пару кнопкой или введите вручную в формате forex GB/XXXXXX",
        reply_markup=_pair_keyboard(),
    )

    return SELECT_PAIR

async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return SELECT_PAIR

    context.user_data["pair_code"] = message.text.strip()

    await message.reply_text(
        "Выберите таймфрейм кнопкой",
        reply_markup=_tick_keyboard(),
    )

    return SELECT_TICK

async def handle_tick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return SELECT_TICK

    text = message.text.strip()

    if text == KB_RESTART:
        return await handle_start(update, context)

    k_type = None

    for item in DEFAULT_TICK_VALUE:
        if item["label"] == text:
            k_type = item["value"]
            break

    if k_type is None:
        await message.reply_text(
            "Выберите таймфрейм кнопкой.",
            reply_markup=_tick_keyboard(),
        )

        return SELECT_TICK

    pair_code = context.user_data.get("pair_code")

    if pair_code is None:
        await message.reply_text("Сначала выберите пару.")

        return await handle_start(update, context)

    MonitorJob(context.job_queue, update.effective_chat.id).add(
        pair_code=pair_code,
        k_type=k_type,
    )

    context.user_data.pop("pair_code", None)

    await message.reply_text(
        f"Мониторинг каждые {MonitorJob.INTERVAL_SEC} с.\n{pair_code}",
        reply_markup=_monitoring_keyboard(),
    )

    return MONITORING


async def handle_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return MONITORING

    text = message.text.strip()
    monitor = MonitorJob(context.job_queue, update.effective_chat.id)

    if text == KB_STOP:
        monitor.remove()

        return await handle_start(update, context)

    if text == KB_AI:
        key = settings.OPEN_ROUTER_API_KEY.strip()

        if not key:
            await message.reply_text(
                "Не задан OPEN_ROUTER_API_KEY (open_router в .env).",
                reply_markup=_monitoring_keyboard(),
            )

            return MONITORING

        now = time.monotonic()
        until = float(context.user_data.get("ai_cooldown_until") or 0.0)

        if now < until:
            left = int(until - now) + 1

            await message.reply_text(
                f"ИИ: не чаще раз в {int(AI_COOLDOWN_SEC)} с. Подожди ещё ~{left} с.",
                reply_markup=_monitoring_keyboard(),
            )

            return MONITORING

        params = monitor.params

        if params is None:
            return await handle_start(update, context)

        pair_code, k_type = params

        context.user_data["ai_cooldown_until"] = now + AI_COOLDOWN_SEC

        await message.reply_text(
            "ИИ: отчёт формируется в фоне (обычно 1–5 мин). \n"
            f"Повторный ИИ — не раньше чем через {int(AI_COOLDOWN_SEC)} с.",
            reply_markup=_monitoring_keyboard(),
        )

        context.application.create_task(
            _deliver_ai_report_background(
                context.application,
                update.effective_chat.id,
                pair_code,
                k_type,
                key,
            ),
            update=update,
        )

        return MONITORING

    if text == KB_REQUEST_DATA:
        params = monitor.params

        if params is None:
            return await handle_start(update, context)

        pair_code, k_type = params
        try:
            result = await asyncio.to_thread(main, pair_code, k_type)

            await message.reply_text(
                Answer.data_snapshot(result),
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=_monitoring_keyboard(),
            )
        except Exception as exc:
            await message.reply_text(
                f"Script execution failed: {exc}",
                reply_markup=_monitoring_keyboard(),
            )

        return MONITORING

    await message.reply_text(
        "Только кнопки: Остановить, Анализ ИИ, Запросить данные.",
        reply_markup=_monitoring_keyboard(),
    )

    return MONITORING


async def _post_init(application: Application) -> None:
    await application.bot.set_my_commands(
        [BotCommand("start", "Начать работу с ботом")],
    )
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def init() -> Application:
    token = settings.BOT_API_KEY.strip()

    if not token:
        raise RuntimeError("Не задан BOT_API_KEY")

    conversation = ConversationHandler(
        entry_points=[
            CommandHandler(
                "start",
                handle_start,
                filters=filters.UpdateType.MESSAGE,
            ),
        ],
        states={
            SELECT_PAIR: [
                MessageHandler(_MSG_TEXT, handle_pair),
            ],
            SELECT_TICK: [
                MessageHandler(_MSG_TEXT, handle_tick),
            ],
            MONITORING: [
                MessageHandler(_MSG_TEXT, handle_monitoring),
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


def run_bot() -> None:
    application = init()

    application.run_polling(
        allowed_updates=[Update.MESSAGE],
        drop_pending_updates=True,
    )
