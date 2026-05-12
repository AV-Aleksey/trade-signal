from typing import TypedDict

from telegram.constants import ParseMode
from telegram.ext import ContextTypes, JobQueue

from internal.answer import Answer
from internal.main import main


class _MonitorData(TypedDict):
    pair_code: str
    k_type: int
    prev_had_signal: bool


class MonitorJob:
    INTERVAL_SEC = 30
    _IMMEDIATE_JOB_SUFFIX = ":immediate"

    def __init__(self, job_queue: JobQueue, chat_id: int) -> None:
        self._job_queue = job_queue
        self._chat_id = chat_id
        self._name = str(chat_id)

    @property
    def _immediate_job_name(self) -> str:
        return f"{self._name}{self._IMMEDIATE_JOB_SUFFIX}"

    def add(self, pair_code: str, k_type: int) -> None:
        self.remove()
        data: _MonitorData = {
            "pair_code": pair_code,
            "k_type": k_type,
            "prev_had_signal": False,
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
    def params(self) -> tuple[str, int] | None:
        jobs = self._job_queue.get_jobs_by_name(self._name)

        if not jobs:
            return None

        data = jobs[0].data

        return data["pair_code"], data["k_type"]

    @staticmethod
    async def _tick(context: ContextTypes.DEFAULT_TYPE) -> None:
        job = context.job
        data = job.data
        try:
            result = main(code=data["pair_code"], k_type=data["k_type"])

            has_signal = bool(result["signals"])

            if has_signal and not data["prev_had_signal"]:
                await context.bot.send_message(
                    chat_id=job.chat_id,
                    text=Answer.monitor_alert(result),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )

            data["prev_had_signal"] = has_signal
        except Exception as exc:
            await context.bot.send_message(
                chat_id=job.chat_id,
                text=f"Ошибка опроса: {exc}",
            )
