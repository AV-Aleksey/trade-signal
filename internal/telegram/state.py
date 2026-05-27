from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionState:
    pair_code: str | None = None
    pending_k_type: int | None = None
    selected_signals: set[str] = field(default_factory=set)
    selected_filters: set[str] = field(default_factory=set)
    ai_cooldown_until: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_code": self.pair_code,
            "pending_k_type": self.pending_k_type,
            "selected_signals": list(self.selected_signals),
            "selected_filters": list(self.selected_filters),
            "ai_cooldown_until": float(self.ai_cooldown_until),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            pair_code=data.get("pair_code"),
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
