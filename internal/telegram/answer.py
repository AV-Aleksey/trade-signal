from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING
from telegram.helpers import escape_markdown

if TYPE_CHECKING:
    from internal.forex.main import MainAnalysisResult

from internal.forex.filter import FilterFlags
from internal.forex.signal import CrossSignalFlags, Signals

EMA_DECIMALS = 5


class SignalType(Enum):
    EMA_UP = ("📈", "EMA 4 пересекает EMA 8 вверх")
    EMA_DOWN = ("📉", "EMA 4 пересекает EMA 8 вниз")
    EMA_8_16_UP = ("📈", "EMA 8 пересекает EMA 16 вверх")
    EMA_8_16_DOWN = ("📉", "EMA 8 пересекает EMA 16 вниз")
    EMA_WC_4_8_UP = ("📈", "EMA WC 4 пересекает EMA WC 8 вверх")
    EMA_WC_4_8_DOWN = ("📉", "EMA WC 4 пересекает EMA WC 8 вниз")
    NONE = ("🔕", "нет активного сигнала")

    def __init__(self, emoji: str, text: str) -> None:
        self.emoji = emoji
        self.text = text


class Answer:
    @staticmethod
    def _format_filter_subsection(title: str, flags: FilterFlags) -> list[str]:
        lines: list[str] = [f"*{escape_markdown(title, version=2)}*"]

        if flags["confirm"]:
            lines.append(
                "✅ "
                + escape_markdown("подтверждает long / блокирует short", version=2),
            )
            lines.append("")

            return lines

        if flags["block"]:
            lines.append(
                "⛔ "
                + escape_markdown("блокирует long / подтверждает short", version=2),
            )
            lines.append("")

            return lines

        lines.append("⚪ " + escape_markdown("нейтрально", version=2))
        lines.append("")

        return lines

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
    def _format_signals_block(
        flags: Signals,
        enabled_keys: frozenset[str] | None = None,
    ) -> str:
        parts: list[str] = []

        if enabled_keys is None or "ema_4_8" in enabled_keys:
            parts.extend(
                Answer._format_cross_subsection(
                    "EMA 4 / EMA 8",
                    flags["ema_4_8"],
                    SignalType.EMA_UP,
                    SignalType.EMA_DOWN,
                ),
            )

        if enabled_keys is None or "ema_8_16" in enabled_keys:
            parts.extend(
                Answer._format_cross_subsection(
                    "EMA 8 / EMA 16",
                    flags["ema_8_16"],
                    SignalType.EMA_8_16_UP,
                    SignalType.EMA_8_16_DOWN,
                ),
            )

        if enabled_keys is None or "ema_wc_4_8" in enabled_keys:
            parts.extend(
                Answer._format_cross_subsection(
                    "EMA WC(HLCC/4) 4x8",
                    flags["ema_wc_4_8"],
                    SignalType.EMA_WC_4_8_UP,
                    SignalType.EMA_WC_4_8_DOWN,
                ),
            )

        while parts and parts[-1] == "":
            parts.pop()

        return "\n".join(parts)

    @staticmethod
    def _format_filters_block(
        flags: dict[str, FilterFlags],
        enabled_keys: frozenset[str] | None = None,
    ) -> str:
        if not enabled_keys:
            return escape_markdown("Фильтры не выбраны", version=2)

        parts: list[str] = []

        if "ema_75" in enabled_keys and "ema_75" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "EMA 75",
                    flags["ema_75"],
                ),
            )

        if "rsi_15" in enabled_keys and "rsi_15" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "RSI 15",
                    flags["rsi_15"],
                ),
            )

        if "stochastic_5_3_3" in enabled_keys and "stochastic_5_3_3" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "Stochastic 5/3/3",
                    flags["stochastic_5_3_3"],
                ),
            )

        if "stochastic_7_5_3" in enabled_keys and "stochastic_7_5_3" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "Stochastic 7/5/3",
                    flags["stochastic_7_5_3"],
                ),
            )

        if "macd_4_5_3" in enabled_keys and "macd_4_5_3" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "MACD 4/5/3",
                    flags["macd_4_5_3"],
                ),
            )

        if "bollinger_20_2" in enabled_keys and "bollinger_20_2" in flags:
            parts.extend(
                Answer._format_filter_subsection(
                    "Bollinger 20/2",
                    flags["bollinger_20_2"],
                ),
            )

        while parts and parts[-1] == "":
            parts.pop()

        if not parts:
            return escape_markdown("Нет данных по выбранным фильтрам", version=2)

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
            e4_wc = row.get("EMA_4_WC")
            e8_wc = row.get("EMA_8_WC")
            close = row.get("close")

            if i:
                chunks.append("")

            chunks.append(f"*{escape_markdown(t, version=2)}*")

            ema_part = f"E4 {e4:.{EMA_DECIMALS}f} · E8 {e8:.{EMA_DECIMALS}f}"

            if e16 is not None:
                ema_part += f" · E16 {float(e16):.{EMA_DECIMALS}f}"

            if e4_wc is not None and e8_wc is not None:
                ema_part += (
                    f" · E4WC {float(e4_wc):.{EMA_DECIMALS}f}"
                    f" · E8WC {float(e8_wc):.{EMA_DECIMALS}f}"
                )

            if close is not None:
                c = float(close)
                val_line = f"C {c:.{EMA_DECIMALS}f} · {ema_part}"
            else:
                val_line = ema_part

            chunks.append(escape_markdown(val_line, version=2))
        return "\n".join(chunks)

    @staticmethod
    def monitor_alert(
        result: MainAnalysisResult,
        enabled_signal_keys: frozenset[str],
        enabled_filter_keys: frozenset[str],
        preset_name: str | None = None,
    ) -> str:
        signals_block = Answer._format_signals_block(
            result["signals"],
            enabled_signal_keys,
        )
        filters_block = Answer._format_filters_block(
            result["filters"],
            enabled_filter_keys,
        )

        parts = [
            escape_markdown("Сигнал 🚨", version=2),
            "",
        ]
        if preset_name:
            parts.append(escape_markdown(f"Пресет: {preset_name}", version=2))
            parts.append("")
        parts.extend(
            [
                escape_markdown(f"Пара: {result['indicator']}", version=2),
                "",
                escape_markdown("Индикаторы (Signals):", version=2),
                signals_block,
                "",
                escape_markdown("Фильтры:", version=2),
                filters_block,
                "",
                escape_markdown("Последние 2 закрытых бара:", version=2),
                Answer._format_candles(result["fresh_candles"]),
            ]
        )

        return "\n".join(parts)

    @staticmethod
    def data_snapshot(
        result: MainAnalysisResult,
        enabled_signal_keys: frozenset[str],
        enabled_filter_keys: frozenset[str],
        preset_name: str | None = None,
    ) -> str:
        signals_block = Answer._format_signals_block(
            result["signals"],
            enabled_signal_keys,
        )
        filters_block = Answer._format_filters_block(
            result["filters"],
            enabled_filter_keys,
        )

        parts = []
        if preset_name:
            parts.append(escape_markdown(f"Пресет: {preset_name}", version=2))
            parts.append("")
        parts.extend(
            [
                escape_markdown(f"Пара: {result['indicator']}", version=2),
                "",
                escape_markdown("Индикаторы (Signals):", version=2),
                signals_block,
                "",
                escape_markdown("Фильтры:", version=2),
                filters_block,
                "",
                escape_markdown("Последние 2 закрытых бара:", version=2),
                Answer._format_candles(result["fresh_candles"]),
            ]
        )

        return "\n".join(parts)
