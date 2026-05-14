from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING
from telegram.helpers import escape_markdown

if TYPE_CHECKING:
    from internal.forex.main import MainAnalysisResult

from internal.forex.signal import CrossSignalFlags, Signals

EMA_DECIMALS = 5

class SignalType(Enum):
    EMA_UP = ("📈", "EMA 4 пересекает EMA 8 вверх")
    EMA_DOWN = ("📉", "EMA 4 пересекает EMA 8 вниз")
    EMA_8_16_UP = ("📈", "EMA 8 пересекает EMA 16 вверх")
    EMA_8_16_DOWN = ("📉", "EMA 8 пересекает EMA 16 вниз")
    MACD_UP = ("📈", "MACD пересекает сигнальную линию вверх")
    MACD_DOWN = ("📉", "MACD пересекает сигнальную линию вниз")
    NONE = ("🔕", "нет активного сигнала")

    def __init__(self, emoji: str, text: str) -> None:
        self.emoji = emoji
        self.text = text


class Answer:
    @staticmethod
    def _format_cross_subsection(
        title: str,
        cross: CrossSignalFlags,
        up_type: SignalType,
        down_type: SignalType,
    ) -> list[str]:
        lines: list[str] = [f"*{escape_markdown(title, version=2)}*"]
        if cross["bullish"]:
            st = up_type
        elif cross["bearish"]:
            st = down_type
        else:
            st = SignalType.NONE

            lines.append(
                f"{st.emoji} "
                + escape_markdown("нет пересечения", version=2),
            )
            lines.append("")

            return lines

        lines.append(f"{st.emoji} {escape_markdown(st.text, version=2)}")
        lines.append("")

        return lines

    @staticmethod
    def _format_signals_block(flags: Signals) -> str:
        parts: list[str] = []

        parts.extend(
            Answer._format_cross_subsection(
                "EMA 4 / EMA 8",
                flags["ema_4_8"],
                SignalType.EMA_UP,
                SignalType.EMA_DOWN,
            ),
        )
        parts.extend(
            Answer._format_cross_subsection(
                "EMA 8 / EMA 16",
                flags["ema_8_16"],
                SignalType.EMA_8_16_UP,
                SignalType.EMA_8_16_DOWN,
            ),
        )
        parts.extend(
            Answer._format_cross_subsection(
                "MACD — линия / сигнал",
                flags["macd"],
                SignalType.MACD_UP,
                SignalType.MACD_DOWN,
            ),
        )

        while parts and parts[-1] == "":
            parts.pop()

        return "\n".join(parts)

    @staticmethod
    def _format_candles(
        rows: list[dict[str, float | int | str]] | None,
    ) -> str:
        if not rows:
            return escape_markdown("Нет 2 баров с EMA", version=2)

        chunks: list[str] = []

        for i, row in enumerate(rows):
            t = str(row["time"])
            e4 = float(row["EMA_4"])
            e8 = float(row["EMA_8"])
            e16 = row.get("EMA_16")
            close = row.get("close")

            if i:
                chunks.append("")

            chunks.append(f"*{escape_markdown(t, version=2)}*")

            ema_part = f"E4 {e4:.{EMA_DECIMALS}f} · E8 {e8:.{EMA_DECIMALS}f}"

            if e16 is not None:
                ema_part += f" · E16 {float(e16):.{EMA_DECIMALS}f}"

            if close is not None:
                c = float(close)
                val_line = f"C {c:.{EMA_DECIMALS}f} · {ema_part}"
            else:
                val_line = ema_part

            chunks.append(escape_markdown(val_line, version=2))
        return "\n".join(chunks)

    @staticmethod
    def monitor_alert(result: MainAnalysisResult) -> str:
        signals_block = Answer._format_signals_block(result["signals"])

        return "\n".join(
            [
                escape_markdown("Сигнал 🚨", version=2),
                "",
                escape_markdown(f"Пара: {result['indicator']}", version=2),
                "",
                escape_markdown("Индикаторы (Signals):", version=2),
                signals_block,
                "",
                escape_markdown("Последние 2 закрытых бара:", version=2),
                Answer._format_candles(result["fresh_candles"]),
            ]
        )

    @staticmethod
    def data_snapshot(result: MainAnalysisResult) -> str:
        signals_block = Answer._format_signals_block(result["signals"])
        
        return "\n".join(
            [
                escape_markdown(f"Пара: {result['indicator']}", version=2),
                "",
                escape_markdown("Индикаторы (Signals):", version=2),
                signals_block,
                "",
                escape_markdown("Последние 2 закрытых бара:", version=2),
                Answer._format_candles(result["fresh_candles"]),
            ]
        )
