from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    pair_code: str | None = None
    selected_preset_ids: set[int] = field(default_factory=set)
    manage_presets_only: bool = False
    # поля для создания пресета
    preset_name: str | None = None
    preset_k_type: int | None = None
    preset_signals: set[str] = field(default_factory=set)
    preset_filters: set[str] = field(default_factory=set)
    pending_k_type: int | None = None  # не используется в новой логике, но оставлен для совместимости
    selected_signals: set[str] = field(default_factory=set)  # совместимость
    selected_filters: set[str] = field(default_factory=set)  # совместимость
    ai_cooldown_until: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_code": self.pair_code,
            "selected_preset_ids": list(self.selected_preset_ids),
            "manage_presets_only": self.manage_presets_only,
            "preset_name": self.preset_name,
            "preset_k_type": self.preset_k_type,
            "preset_signals": list(self.preset_signals),
            "preset_filters": list(self.preset_filters),
            "pending_k_type": self.pending_k_type,
            "selected_signals": list(self.selected_signals),
            "selected_filters": list(self.selected_filters),
            "ai_cooldown_until": float(self.ai_cooldown_until),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            pair_code=data.get("pair_code"),
            selected_preset_ids=set(data.get("selected_preset_ids") or []),
            manage_presets_only=bool(data.get("manage_presets_only") or False),
            preset_name=data.get("preset_name"),
            preset_k_type=data.get("preset_k_type"),
            preset_signals=set(data.get("preset_signals") or []),
            preset_filters=set(data.get("preset_filters") or []),
            pending_k_type=data.get("pending_k_type"),
            selected_signals=set(data.get("selected_signals") or []),
            selected_filters=set(data.get("selected_filters") or []),
            ai_cooldown_until=float(data.get("ai_cooldown_until") or 0.0),
        )


class SessionStateStore:
    KEY = "session_state"

    def load(self, context: Any) -> SessionState:
        raw = context.user_data.get(self.KEY)

        if isinstance(raw, dict):
            return SessionState.from_dict(raw)

        return SessionState()

    def save(self, context: Any, state: SessionState) -> None:
        context.user_data[self.KEY] = state.to_dict()

    def reset(self, context: Any) -> SessionState:
        context.user_data.pop(self.KEY, None)

        return SessionState()
