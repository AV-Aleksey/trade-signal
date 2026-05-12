from typing import TypedDict

import pandas as pd
from telegram.helpers import escape_markdown

_TELEGRAM_MESSAGE_MAX_CHARS = 4096
_DATA_FRAME_SAFE_MAX_CHARS = 3800
_EMA_DECIMALS = 5


class MainAnalysisResult(TypedDict):
    indicator: str
    signals: list[dict[str, bool]]
    ema_last_two_rows: list[dict[str, float | int | str]] | None
    data_frame: pd.DataFrame


class Answer:
    @staticmethod
    def _md_v2(text: str) -> str:
        return escape_markdown(text, version=2)

    @staticmethod
    def _md_v2_bold(text: str) -> str:
        return f"*{escape_markdown(text, version=2)}*"

    @staticmethod
    def _format_signals_block_md_v2(signals: list[dict[str, bool]]) -> str:
        if not signals:
            return f"🔕 {Answer._md_v2('нет активного сигнала')}"
        lines: list[str] = []
        for payload in signals:
            emoji = "📈" if payload.get("up") else "📉"
            line = Answer._signal_payload_to_line(payload)
            lines.append(f"{emoji} {Answer._md_v2(line)}")
        return "\n".join(lines)

    @staticmethod
    def _signal_payload_to_line(payload: dict[str, bool]) -> str:
        if payload.get("up"):
            return "EMA 4 пересекает EMA 8 вверх"
        return "EMA 4 пересекает EMA 8 вниз"

    @staticmethod
    def _format_ema_last_two_md_v2(
        rows: list[dict[str, float | int | str]] | None,
    ) -> str:
        if not rows:
            return Answer._md_v2("Нет 2 баров с EMA")
        chunks: list[str] = []
        for i, row in enumerate(rows):
            rid = int(row["id"])
            t = str(row["time"])
            e4 = float(row["ema4"])
            e8 = float(row["ema8"])
            close_v = row.get("close")

            if i:
                chunks.append("")
            id_line = f"бар №{rid} (индекс строки в DataFrame) · {t}"
            chunks.append(Answer._md_v2_bold(id_line))
            if close_v is not None:
                c = float(close_v)
                val_line = (
                    f"C {c:.{_EMA_DECIMALS}f} · E4 {e4:.{_EMA_DECIMALS}f} · "
                    f"E8 {e8:.{_EMA_DECIMALS}f}"
                )
            else:
                val_line = (
                    f"E4 {e4:.{_EMA_DECIMALS}f} · E8 {e8:.{_EMA_DECIMALS}f}"
                )
            chunks.append(Answer._md_v2(val_line))
        return "\n".join(chunks)

    @staticmethod
    def monitor_alert(result: MainAnalysisResult) -> str:
        return "\n".join(
            [
                Answer._md_v2("Сигнал"),
                "",
                Answer._md_v2(f"Пара: {result['indicator']}"),
                "",
                Answer._md_v2("Сигналы:"),
                Answer._format_signals_block_md_v2(result["signals"]),
                "",
                Answer._md_v2("EMA последние 2 бара:"),
                Answer._format_ema_last_two_md_v2(result["ema_last_two_rows"]),
            ]
        )

    @staticmethod
    def data_snapshot(result: MainAnalysisResult) -> str:
        return "\n".join(
            [
                Answer._md_v2(f"Пара: {result['indicator']}"),
                "",
                Answer._md_v2("Сигналы:"),
                Answer._format_signals_block_md_v2(result["signals"]),
                "",
                Answer._md_v2("EMA последние 2 бара:"),
                Answer._format_ema_last_two_md_v2(result["ema_last_two_rows"]),
            ]
        )

    @staticmethod
    def data_frame(
        df: pd.DataFrame,
        *,
        max_chars: int = _DATA_FRAME_SAFE_MAX_CHARS,
        max_rows: int = 80,
        max_cols: int = 40,
    ) -> str:
        capped = min(max_chars, _TELEGRAM_MESSAGE_MAX_CHARS - 64)
        body = df.to_string(max_rows=max_rows, max_cols=max_cols)

        if len(body) <= capped:
            return body
        suffix = "\n… (обрезано)"
        head_len = max(0, capped - len(suffix))

        return body[:head_len].rstrip() + suffix
