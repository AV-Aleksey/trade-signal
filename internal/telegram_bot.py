import asyncio

from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from internal.config import settings
from internal.main import main

KB_RESTART = "Начать заново"
KB_STOP = "Остановить"
KB_AI = "Анализ ИИ"
KB_REQUEST_DATA = "Запросить данные"

DEFAULT_PICK_PAIR = ["GB/GBPJPY", "GB/EURUSD", "GB/XAUUSD"]
DEFAULT_TICK_VALUE = [
    {"label": "1 минута", "value": 1},
    {"label": "15 минут", "value": 2},
    {"label": "30 минут", "value": 3},
]

SELECT_PAIR, SELECT_TICK, MONITORING = range(3)

MONITOR_INTERVAL_SEC = 30


def _monitoring_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=KB_STOP)],
        [KeyboardButton(text=KB_AI), KeyboardButton(text=KB_REQUEST_DATA)],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


async def _stop_monitoring_task(user_data: dict) -> None:
    user_data["monitoring_active"] = False
    task = user_data.pop("monitor_task", None)
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    user_data.pop("monitor_pair_code", None)
    user_data.pop("monitor_k_type", None)
    user_data.pop("monitor_prev_had_signal", None)


async def _monitoring_poll_loop(bot, chat_id: int, user_data: dict) -> None:
    try:
        while user_data.get("monitoring_active"):
            await asyncio.sleep(MONITOR_INTERVAL_SEC)

            if not user_data.get("monitoring_active"):
                break

            pair_code = user_data.get("monitor_pair_code")
            k_type = user_data.get("monitor_k_type")

            if pair_code is None or k_type is None:
                break
            try:
                result = main(code=pair_code, k_type=k_type)
                has_signal = bool(result["signals"])
                prev = user_data.get("monitor_prev_had_signal", False)

                if has_signal and not prev:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"Сигнал:\n{result['indicator']}\n"
                        + "\n".join(result["signals"]),
                    )

                user_data["monitor_prev_had_signal"] = has_signal
            except Exception as exc:
                await bot.send_message(chat_id=chat_id, text=f"Ошибка опроса: {exc}")
    except asyncio.CancelledError:
        pass


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return ConversationHandler.END

    await _stop_monitoring_task(context.user_data)
    context.user_data.pop("pair_code", None)

    pair_rows = [[KeyboardButton(text=pair)] for pair in DEFAULT_PICK_PAIR]

    pair_keyboard = ReplyKeyboardMarkup(
        pair_rows,
        resize_keyboard=True,
        input_field_placeholder="GB/EURUSD или кнопка ниже",
    )

    await message.reply_text(
        "Выберите валютную пару кнопкой или введите вручную в формате forex GB/XXXXXX",
        reply_markup=pair_keyboard,
    )

    return SELECT_PAIR


async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return SELECT_PAIR

    context.user_data["pair_code"] = message.text.strip()

    tick_rows = [[KeyboardButton(text=item["label"])] for item in DEFAULT_TICK_VALUE]
    tick_rows.append([KeyboardButton(text=KB_RESTART)])

    tick_keyboard = ReplyKeyboardMarkup(
        tick_rows,
        resize_keyboard=True,
        input_field_placeholder="например: 1 минута",
    )

    await message.reply_text(
        "Выберите таймфрейм кнопкой",
        reply_markup=tick_keyboard,
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
        await message.reply_text("Выберите таймфрейм кнопкой.")

        return SELECT_TICK

    pair_code = context.user_data.get("pair_code")

    if pair_code is None:
        await message.reply_text("Сначала выберите пару.")

        return await handle_start(update, context)

    await _stop_monitoring_task(context.user_data)

    user_data = context.user_data
    user_data["monitoring_active"] = True
    user_data["monitor_pair_code"] = pair_code
    user_data["monitor_k_type"] = k_type
    user_data["monitor_prev_had_signal"] = False
    user_data["monitor_task"] = asyncio.create_task(
        _monitoring_poll_loop(
            context.bot,
            update.effective_chat.id,
            user_data,
        )
    )

    context.user_data.pop("pair_code", None)

    await message.reply_text(
        f"Мониторинг каждые {MONITOR_INTERVAL_SEC} с.\n{pair_code}",
        reply_markup=_monitoring_keyboard(),
    )

    return MONITORING


async def handle_monitoring(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return MONITORING

    text = message.text.strip()

    if text == KB_STOP:
        await _stop_monitoring_task(context.user_data)

        return await handle_start(update, context)

    if text == KB_AI:
        await message.reply_text(
            "Анализ ИИ: в разработке.",
            reply_markup=_monitoring_keyboard(),
        )

        return MONITORING

    if text == KB_REQUEST_DATA:
        pair_code = context.user_data.get("monitor_pair_code")
        k_type = context.user_data.get("monitor_k_type")

        if pair_code is None or k_type is None:
            await _stop_monitoring_task(context.user_data)

            return await handle_start(update, context)

        try:
            result = main(code=pair_code, k_type=k_type)

            signal_lines = (
                "\n".join(result["signals"])
                if result["signals"]
                else "Нет сигнала"
            )
            await message.reply_text(
                f"{result['indicator']}\n{signal_lines}",
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


def init() -> Application:
    token = settings.BOT_API_KEY.strip()

    if not token:
        raise RuntimeError("Не задан BOT_API_KEY")

    conversation = ConversationHandler(
        entry_points=[CommandHandler("start", handle_start)],
        states={
            SELECT_PAIR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pair),
            ],
            SELECT_TICK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tick),
            ],
            MONITORING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_monitoring),
            ],
        },
        fallbacks=[CommandHandler("start", handle_start)],
    )

    application = Application.builder().token(token).build()
    application.add_handler(conversation)

    return application


def run_bot() -> None:
    application = init()

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
