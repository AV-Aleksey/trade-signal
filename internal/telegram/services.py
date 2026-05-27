from __future__ import annotations

import asyncio
from dataclasses import dataclass

from internal.ai.main import OpenRouter, OpenRouterRateLimitError
from internal.ai.ta_ai import TA_SYSTEM_PROMPT, build_ta_user_message
from internal.forex.itick import ItickUnavailableError
from internal.forex.main import main
from internal.telegram.answer import Answer


class AiReportError(Exception):
    pass


class AiReportRateLimitError(AiReportError):
    pass


@dataclass
class AiReportResult:
    text: str


class AiReportService:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @property
    def has_api_key(self) -> bool:
        return bool(self._api_key.strip())

    @staticmethod
    def _prepare_user_message(pair_code: str, k_type: int) -> str:
        result = main(code=pair_code, k_type=k_type)

        return build_ta_user_message(
            pair=pair_code,
            k_type=k_type,
            df=result["data_frame"],
        )

    async def generate(self, pair_code: str, k_type: int) -> AiReportResult:
        try:
            user_block = await asyncio.to_thread(
                self._prepare_user_message,
                pair_code,
                k_type,
            )
        except ItickUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise AiReportError(f"Данные для ИИ: {exc}") from exc

        try:
            client = OpenRouter(api_key=self._api_key)
            reply = await asyncio.to_thread(
                client.chat,
                user_block,
                system_content=TA_SYSTEM_PROMPT,
            )

            return AiReportResult(text=reply[:4096])
        except OpenRouterRateLimitError as exc:
            raise AiReportRateLimitError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise AiReportError(f"OpenRouter: {exc}") from exc


class DataSnapshotService:
    async def fetch(
        self,
        pair_code: str,
        k_type: int,
        enabled_filters: frozenset[str],
        enabled_signals: frozenset[str],
    ) -> str:
        try:
            result = await asyncio.to_thread(
                main,
                pair_code,
                k_type,
                enabled_filters,
            )
        except ItickUnavailableError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(str(exc)) from exc

        return Answer.data_snapshot(result, enabled_signals, enabled_filters)
