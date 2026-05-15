from typing import TypedDict

from telegram.constants import ParseMode
from telegram.ext import ContextTypes, JobQueue

from internal.forex.main import main
from internal.forex.signal import CrossSignalFlags, Signals
from internal.telegram.answer import Answer


def _cross_flags_for_signal_key(signals: Signals, key: str) -> CrossSignalFlags | None:
    if key == "ema_4_8":
        return signals["ema_4_8"]

    if key == "ema_8_16":
        return signals["ema_8_16"]

    if key == "macd":
        return signals["macd"]

    return None


def _is_cross_active(signals: Signals, key: str) -> bool:
    block = _cross_flags_for_signal_key(signals, key)

    return block is not None and (block["bullish"] or block["bearish"])


class _MonitorData(TypedDict):
    pair_code: str
    k_type: int
    enabled_signal_keys: frozenset[str]
    prev_active_by_key: dict[str, bool]


class MonitorJob:
    INTERVAL_SEC = 60
    IMMEDIATE_JOB_SUFFIX = ":immediate"

    def __init__(self, job_queue: JobQueue, chat_id: int) -> None:
        self._job_queue = job_queue
        self._chat_id = chat_id
        self._name = str(chat_id)

    @property
    def _immediate_job_name(self) -> str:
        return f"{self._name}{self.IMMEDIATE_JOB_SUFFIX}"

    def add(
        self,
        pair_code: str,
        k_type: int,
        enabled_signal_keys: frozenset[str],
    ) -> None:
        self.remove()

        data: _MonitorData = {
            "pair_code": pair_code,
            "k_type": k_type,
            "enabled_signal_keys": enabled_signal_keys,
            "prev_active_by_key": {k: False for k in enabled_signal_keys},
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
    def params(self) -> tuple[str, int, frozenset[str]] | None:
        jobs = self._job_queue.get_jobs_by_name(self._name)

        if not jobs:
            return None

        data = jobs[0].data

        return (
            data["pair_code"],
            data["k_type"],
            data["enabled_signal_keys"],
        )

    @staticmethod
    async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
        job = context.job
        data = job.data

        try:
            result = main(code=data["pair_code"], k_type=data["k_type"])

            signals = result["signals"]
            enabled = data["enabled_signal_keys"]
            prev_by = data["prev_active_by_key"]

            has_rising_edge = False

            for key in enabled:
                now = _is_cross_active(signals, key)
                was = prev_by.get(key, False)

                if now and not was:
                    has_rising_edge = True

                    break

            if has_rising_edge:
                await context.bot.send_message(
                    chat_id=job.chat_id,
                    text=Answer.monitor_alert(
                        result,
                        data["enabled_signal_keys"],
                    ),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )

            data["prev_active_by_key"] = {
                k: _is_cross_active(signals, k) for k in enabled
            }
        except Exception as exc:
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=f"Ошибка опроса: {exc}",
            )
