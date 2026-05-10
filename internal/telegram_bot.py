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

DEFAULT_PICK_PAIR = ["GB/GBPJPY", "GB/EURUSD", "GB/XAUUSD"]
DEFAULT_TICK_VALUE = [
    {"label": "1 минута", "value": 1},
    {"label": "15 минут", "value": 2},
    {"label": "30 минут", "value": 3},
]

SELECT_PAIR, SELECT_TICK = range(2)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message

    if message is None:
        return ConversationHandler.END

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

    pair_rows = [[KeyboardButton(text=pair)] for pair in DEFAULT_PICK_PAIR]
    next_pair_keyboard = ReplyKeyboardMarkup(
        pair_rows,
        resize_keyboard=True,
        input_field_placeholder="GB/EURUSD или кнопка ниже",
    )

    try:
        result = main(code=pair_code, k_type=k_type)

        await message.reply_text(
            f"{result['indicator']}\n{result['signal']}",
            reply_markup=next_pair_keyboard,
        )
    except Exception as exc:
        await message.reply_text(
            f"Script execution failed: {exc}",
            reply_markup=next_pair_keyboard,
        )

    context.user_data.pop("pair_code", None)

    return SELECT_PAIR


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
