from telegram.ext import ContextTypes

from internal.telegram import texts, ui
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import SELECT_TICK


def make_pair_handler(state_store: SessionStateStore):
    async def handle_pair(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_TICK

        state = state_store.load(context)
        state.pair_code = message.text.strip()
        state_store.save(context, state)

        await message.reply_text(
            texts.SELECT_TICK_PROMPT,
            reply_markup=ui.tick_keyboard(),
        )

        return SELECT_TICK

    return handle_pair
