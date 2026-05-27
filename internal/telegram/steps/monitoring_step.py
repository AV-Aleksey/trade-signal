import time

from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from internal.forex.itick import ItickUnavailableError
from internal.telegram import texts, ui
from internal.telegram.monitor_job import MonitorJob
from internal.telegram.services import (
    AiReportError,
    AiReportRateLimitError,
    AiReportService,
    DataSnapshotService,
)
from internal.telegram.state import SessionStateStore
from internal.telegram.steps.flow import MONITORING

AI_COOLDOWN_SEC = 60.0


async def _deliver_ai_report(
    application,
    chat_id: int,
    service: AiReportService,
    pair_code: str,
    k_type: int,
) -> None:
    try:
        result = await service.generate(pair_code, k_type)
        await application.bot.send_message(
            chat_id=chat_id,
            text=result.text,
            reply_markup=ui.monitoring_keyboard(),
        )
    except ItickUnavailableError as exc:
        MonitorJob(application.job_queue, chat_id).remove()
        await application.bot.send_message(
            chat_id=chat_id,
            text=str(exc),
            reply_markup=ui.pair_keyboard(),
        )
    except AiReportRateLimitError as exc:
        await application.bot.send_message(
            chat_id=chat_id,
            text=str(exc),
            reply_markup=ui.monitoring_keyboard(),
        )
    except AiReportError as exc:
        await application.bot.send_message(
            chat_id=chat_id,
            text=str(exc),
            reply_markup=ui.monitoring_keyboard(),
        )
    except Exception as exc:  # pragma: no cover - defensive
        await application.bot.send_message(
            chat_id=chat_id,
            text=f"OpenRouter: {exc}",
            reply_markup=ui.monitoring_keyboard(),
        )


def make_monitoring_handler(
    state_store: SessionStateStore,
    restart_handler,
    ai_service: AiReportService,
    snapshot_service: DataSnapshotService,
):
    async def handle_monitoring(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return MONITORING

        text = message.text.strip()
        monitor = MonitorJob(context.job_queue, update.effective_chat.id)

        if text == ui.KB_STOP:
            monitor.remove()

            return await restart_handler(update, context)

        if text == ui.KB_AI:
            if not ai_service.has_api_key:
                await message.reply_text(
                    texts.OPEN_ROUTER_MISSING,
                    reply_markup=ui.monitoring_keyboard(),
                )

                return MONITORING

            now = time.monotonic()
            state = state_store.load(context)
            until = float(state.ai_cooldown_until or 0.0)

            if now < until:
                left = int(until - now) + 1

                await message.reply_text(
                    texts.AI_COOLDOWN_WAIT.format(seconds=left),
                    reply_markup=ui.monitoring_keyboard(),
                )

                return MONITORING

            params = monitor.params

            if params is None:
                return await restart_handler(update, context)

            pair_code, k_type, _enabled_keys, _enabled_filters = params
            state.ai_cooldown_until = now + AI_COOLDOWN_SEC
            state_store.save(context, state)

            await message.reply_text(
                texts.AI_IN_PROGRESS.format(cooldown=int(AI_COOLDOWN_SEC)),
                reply_markup=ui.monitoring_keyboard(),
            )

            context.application.create_task(
                _deliver_ai_report(
                    context.application,
                    update.effective_chat.id,
                    ai_service,
                    pair_code,
                    k_type,
                ),
                update=update,
            )

            return MONITORING

        if text == ui.KB_REQUEST_DATA:
            params = monitor.params

            if params is None:
                return await restart_handler(update, context)

            pair_code, k_type, enabled_keys, enabled_filters = params

            try:
                snapshot = await snapshot_service.fetch(
                    pair_code,
                    k_type,
                    enabled_filters,
                    enabled_keys,
                )
                await message.reply_text(
                    snapshot,
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ui.monitoring_keyboard(),
                )
            except ItickUnavailableError as exc:
                monitor.remove()
                await message.reply_text(
                    str(exc),
                    reply_markup=ui.pair_keyboard(),
                )
            except Exception as exc:  # pragma: no cover - defensive
                await message.reply_text(
                    texts.SCRIPT_FAILED.format(error=exc),
                    reply_markup=ui.monitoring_keyboard(),
                )

            return MONITORING

        await message.reply_text(
            texts.ONLY_MONITOR_BUTTONS.format(
                stop=ui.KB_STOP,
                ai=ui.KB_AI,
                request_data=ui.KB_REQUEST_DATA,
            ),
            reply_markup=ui.monitoring_keyboard(),
        )

        return MONITORING

    return handle_monitoring
