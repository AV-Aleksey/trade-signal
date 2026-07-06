from typing import TypedDict

from telegram.constants import ParseMode
from telegram.ext import ContextTypes, JobQueue

from internal.forex.filter import FilterFlags
from internal.forex.itick import ItickUnavailableError, MissingItickTokenError
from internal.forex.main import main
from internal.forex.signal import CrossSignalFlags, Signals
from internal.telegram.answer import Answer
from internal.telegram import texts


def _cross_flags_for_signal_key(signals: Signals, key: str) -> CrossSignalFlags | None:
    if key == "ema_4_8":
        return signals["ema_4_8"]

    if key == "ema_8_16":
        return signals["ema_8_16"]

    if key == "ema_wc_4_8":
        return signals["ema_wc_4_8"]

    return None


def _is_cross_active(signals: Signals, key: str) -> bool:
    block = _cross_flags_for_signal_key(signals, key)

    return block is not None and (block["bullish"] or block["bearish"])


def _is_signal_blocked_by_filters(
    signals: Signals,
    signal_key: str,
    filters: dict[str, FilterFlags],
) -> bool:
    signal_flags = _cross_flags_for_signal_key(signals, signal_key)

    if signal_flags is None:
        return True

    if signal_flags["bullish"]:
        return any(flags["block"] for flags in filters.values())

    if signal_flags["bearish"]:
        return any(flags["confirm"] for flags in filters.values())

    return True


class _MonitorData(TypedDict):
    pair_code: str
    telegram_user_id: int
    presets: list[dict]  # [{id,name,k_type,signal_keys,set filter_keys,set prev_by_key:dict}]


class MonitorJob:
    INTERVAL_SEC = 60
    IMMEDIATE_JOB_SUFFIX = ":immediate"

    def __init__(
        self,
        job_queue: JobQueue,
        chat_id: int,
    ) -> None:
        self._job_queue = job_queue
        self._chat_id = chat_id
        self._name = str(chat_id)

    @property
    def _immediate_job_name(self) -> str:
        return f"{self._name}{self.IMMEDIATE_JOB_SUFFIX}"

    def add(
        self,
        pair_code: str,
        telegram_user_id: int,
        presets: list[dict],
    ) -> None:
        self.remove()

        data: _MonitorData = {
            "pair_code": pair_code,
            "telegram_user_id": telegram_user_id,
            "presets": presets,
        }

        self._job_queue.run_once(
            self._tick,
            when=0,
            name=self._immediate_job_name,
            chat_id=self._chat_id,
            data=data,
        )

        self._job_queue.run_repeating(
            self._tick,
            interval=self.INTERVAL_SEC,
            first=self.INTERVAL_SEC,
            name=self._name,
            chat_id=self._chat_id,
            data=data,
        )

    def remove(self) -> None:
        for job in self._job_queue.get_jobs_by_name(self._name):
            job.schedule_removal()

        for job in self._job_queue.get_jobs_by_name(self._immediate_job_name):
            job.schedule_removal()

    @property
    def params(self) -> tuple[str, list[dict]] | None:
        jobs = self._job_queue.get_jobs_by_name(self._name)

        if not jobs:
            return None

        data = jobs[0].data

        return (
            data["pair_code"],
            data["presets"],
        )

    @staticmethod
    async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
        job = context.job
        data = job.data

        try:
            user_id = data["telegram_user_id"]
            pair_code = data["pair_code"]
            presets = data["presets"]

            for preset in presets:
                k_type = int(preset["k_type"])
                signal_keys = set(preset["signal_keys"])
                filter_keys = set(preset["filter_keys"])
                prev_by = preset.get("prev_by_key") or {k: False for k in signal_keys}

                result = main(
                    code=pair_code,
                    k_type=k_type,
                    enabled_filter_keys=filter_keys,
                    telegram_user_id=user_id,
                )

                signals = result["signals"]
                filters = result["filters"]

                has_rising = False
                for key in signal_keys:
                    now = _is_cross_active(signals, key)
                    was = prev_by.get(key, False)
                    if now and not was and not _is_signal_blocked_by_filters(signals, key, filters):
                        has_rising = True
                        break

                if has_rising:
                    await context.bot.send_message(
                        chat_id=job.chat_id,
                        text=Answer.monitor_alert(
                            result,
                            signal_keys,
                            filter_keys,
                            preset_name=preset.get("name", ""),
                        ),
                        parse_mode=ParseMode.MARKDOWN_V2,
                    )

                preset["prev_by_key"] = {k: _is_cross_active(signals, k) for k in signal_keys}
        except MissingItickTokenError:
            MonitorJob(context.job_queue, job.chat_id).remove()
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=texts.ITICK_TOKEN_REQUIRED,
            )
        except ItickUnavailableError as exc:
            MonitorJob(context.job_queue, job.chat_id).remove()
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=str(exc),
            )
        except Exception as exc:
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=f"Ошибка опроса: {exc}",
            )
