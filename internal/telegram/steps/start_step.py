from telegram.ext import ConversationHandler, ContextTypes

from internal.telegram import texts, ui
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import SELECT_PAIR
from internal.telegram.monitor_job import MonitorJob


def make_start_handler(state_store: SessionStateStore):
    async def handle_start(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return ConversationHandler.END

        MonitorJob(context.job_queue, update.effective_chat.id).remove()

        state = state_store.reset(context)
        state_store.save(context, state)

        await message.reply_text(
            texts.START_PAIR_PROMPT,
            reply_markup=ui.pair_keyboard(),
        )

        return SELECT_PAIR

    return handle_start
