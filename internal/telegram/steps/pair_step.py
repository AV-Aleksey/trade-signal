from telegram.ext import ContextTypes

from internal.storage.preset_repository import UserSignalPresetRepository
from internal.telegram import texts, ui
from internal.telegram.auth import AuthService
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import SELECT_PRESETS


def make_pair_handler(
    state_store: SessionStateStore,
    preset_repo: UserSignalPresetRepository,
    auth_service: AuthService,
):
    async def handle_pair(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_PRESETS

        user = update.effective_user
        if user is None or not auth_service.is_authorized(int(user.id)):
            await message.reply_text(
                "🚫 Доступ запрещён. Выполните /auth и отправьте токен.",
                reply_markup=ui.pair_keyboard(),
            )
            return SELECT_PRESETS

        state = state_store.load(context)
        text = message.text.strip()

        state.pair_code = text
        state.manage_presets_only = False
        state_store.save(context, state)

        presets = preset_repo.list_presets(int(user.id))
        if not presets:
            await message.reply_text(
                "У вас еще нет настроенных сигналов, настройте их в главном меню бота",
                reply_markup=ui.pair_keyboard(),
            )
            return SELECT_PRESETS

        await message.reply_text(
            texts.PRESET_SELECT_FOR_MONITOR,
            reply_markup=ui.preset_selection_keyboard(presets, set()),
        )

        return SELECT_PRESETS

    return handle_pair
