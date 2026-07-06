from telegram.ext import ContextTypes

from internal.storage.preset_repository import UserSignalPresetRepository
from internal.telegram.auth import AuthService
from internal.telegram import texts, ui
from internal.telegram.monitor_job import MonitorJob
from internal.telegram.state import SessionState, SessionStateStore
from internal.telegram.steps.flow import MONITORING, SELECT_PRESETS


async def start_monitoring_presets(
    update,
    context: ContextTypes.DEFAULT_TYPE,
    state_store: SessionStateStore,
    preset_repository: UserSignalPresetRepository,
    auth_service: AuthService,
    pair_code: str,
    selected_preset_ids: set[int],
) -> int:
    user = update.effective_user

    if user is None or not auth_service.is_authorized(int(user.id)):
        await update.message.reply_text(
            "🚫 Доступ запрещён. Выполните /auth и отправьте токен.",
            reply_markup=ui.pair_keyboard(),
        )

        return SELECT_PRESETS

    telegram_user_id = int(user.id)
    presets_all = preset_repository.list_presets(telegram_user_id)
    presets = [p for p in presets_all if int(p["id"]) in selected_preset_ids]

    if not presets:
        await update.message.reply_text(
            texts.PRESET_NEED_SELECT,
            reply_markup=ui.preset_selection_keyboard(presets_all, set()),
        )
        return SELECT_PRESETS

    # нормализуем наборы
    normalized = []
    for p in presets:
        normalized.append(
            {
                "id": int(p["id"]),
                "name": str(p["name"]),
                "k_type": int(p["k_type"]),
                "signal_keys": set(p["signal_ids"]),
                "filter_keys": set(p["filter_ids"]),
                "prev_by_key": {k: False for k in p["signal_ids"]},
            }
        )

    MonitorJob(
        context.job_queue,
        update.effective_chat.id,
    ).add(
        pair_code=pair_code,
        telegram_user_id=telegram_user_id,
        presets=normalized,
    )

    state_store.save(context, SessionState(ai_cooldown_until=0.0))

    await update.message.reply_text(
        f"Мониторинг каждые {MonitorJob.INTERVAL_SEC} с.\n{pair_code}\n"
        f"Пресеты: {', '.join(p['name'] for p in normalized)}",
        reply_markup=ui.monitoring_keyboard(),
    )

    return MONITORING
