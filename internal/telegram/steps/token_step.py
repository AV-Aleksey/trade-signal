from telegram.ext import ContextTypes

from internal.storage.itick_token_repository import ItickTokenRepository
from internal.telegram import texts, ui
from internal.telegram.steps.flow import INPUT_ITICK_TOKEN, SELECT_PAIR


def make_token_handler(
    itick_token_repository: ItickTokenRepository,
):
    async def handle_token(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return INPUT_ITICK_TOKEN

        text = message.text.strip()

        if text == ui.KB_RESTART:
            await message.reply_text(
                texts.START_PAIR_PROMPT,
                reply_markup=ui.pair_keyboard(),
            )

            return SELECT_PAIR

        user = update.effective_user

        if user is None:
            await message.reply_text(
                texts.ITICK_TOKEN_REQUIRED,
                reply_markup=ui.pair_keyboard(),
            )

            return SELECT_PAIR

        try:
            itick_token_repository.update_itick_token(
                telegram_user_id=int(user.id),
                token=text,
            )
        except Exception as exc:
            await message.reply_text(
                texts.SCRIPT_FAILED.format(error=exc),
                reply_markup=ui.token_input_keyboard(),
            )

            return INPUT_ITICK_TOKEN

        await message.reply_text(
            texts.ITICK_TOKEN_SAVED,
            reply_markup=ui.pair_keyboard(),
        )

        return SELECT_PAIR

    return handle_token


def make_itick_entry_handler():
    async def handle_itick_entry(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return INPUT_ITICK_TOKEN

        await message.reply_text(
            texts.ITICK_TOKEN_PROMPT,
            reply_markup=ui.token_input_keyboard(),
        )

        return INPUT_ITICK_TOKEN

    return handle_itick_entry
