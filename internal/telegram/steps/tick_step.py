from telegram.ext import ContextTypes

from internal.telegram import options, texts, ui
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import SELECT_SIGNALS, SELECT_TICK


def make_tick_handler(state_store: SessionStateStore, restart_handler):
    async def handle_tick(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_TICK

        text = message.text.strip()

        if text == ui.KB_RESTART:
            return await restart_handler(update, context)

        k_type = options.find_tick_value(text)

        if k_type is None:
            await message.reply_text(
                texts.INVALID_TICK_PROMPT,
                reply_markup=ui.tick_keyboard(),
            )

            return SELECT_TICK

        state = state_store.load(context)

        if state.pair_code is None:
            await message.reply_text(texts.NEED_PAIR_FIRST)

            return await restart_handler(update, context)

        state.pending_k_type = k_type
        state.selected_signals = set()
        state.selected_filters = set()
        state_store.save(context, state)

        await message.reply_text(
            texts.SELECT_SIGNAL_PROMPT.format(
                select_all=ui.KB_SIGNAL_SELECT_ALL,
                done=ui.KB_SIGNAL_DONE,
            ),
            reply_markup=ui.signal_selection_keyboard(set()),
        )

        return SELECT_SIGNALS

    return handle_tick
