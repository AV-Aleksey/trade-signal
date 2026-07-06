from telegram.ext import ContextTypes

from internal.telegram import options, texts, ui
from internal.telegram.monitor_job import MonitorJob
from internal.telegram.state import SessionState, SessionStateStore
from internal.telegram.steps.flow import MONITORING, SELECT_PAIR


async def start_monitoring(
    update,
    context: ContextTypes.DEFAULT_TYPE,
    state_store: SessionStateStore,
    pair_code: str,
    k_type: int,
    selected_signals: set[str],
    selected_filters: frozenset[str],
) -> int:
    user = update.effective_user

    if user is None:
        await update.message.reply_text(
            texts.ITICK_TOKEN_REQUIRED,
            reply_markup=ui.pair_keyboard(),
        )

        return SELECT_PAIR

    telegram_user_id = int(user.id)

    MonitorJob(
        context.job_queue,
        update.effective_chat.id,
    ).add(
        pair_code=pair_code,
        k_type=k_type,
        telegram_user_id=telegram_user_id,
        enabled_signal_keys=frozenset(selected_signals),
        enabled_filter_keys=selected_filters,
    )

    state_store.save(context, SessionState(ai_cooldown_until=0.0))

    await update.message.reply_text(
        f"Мониторинг каждые {MonitorJob.INTERVAL_SEC} с.\n{pair_code}\n"
        f"Сигналы: {options.summarize_signal_keys(selected_signals)}\n"
        f"Фильтры: {options.summarize_filter_keys(selected_filters)}",
        reply_markup=ui.monitoring_keyboard(),
    )

    return MONITORING
