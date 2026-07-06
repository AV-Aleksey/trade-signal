from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from internal.config import settings

MAX_PRESETS_PER_USER = 3


class UserSignalPresetRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = Path(db_path or settings.SQLITE_DB_PATH).expanduser()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_signal_presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    k_type INTEGER NOT NULL,
                    signal_ids TEXT NOT NULL,
                    filter_ids TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(telegram_user_id, name)
                )
                """,
            )
            connection.commit()

    def list_presets(self, telegram_user_id: int) -> list[dict]:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, name, k_type, signal_ids, filter_ids, created_at, updated_at
                FROM user_signal_presets
                WHERE telegram_user_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (telegram_user_id,),
            )
            rows = cursor.fetchall()

        result: list[dict] = []
        for row in rows:
            preset_id, name, k_type, signal_ids, filter_ids, created_at, updated_at = row
            result.append(
                {
                    "id": int(preset_id),
                    "name": str(name),
                    "k_type": int(k_type),
                    "signal_ids": json.loads(signal_ids),
                    "filter_ids": json.loads(filter_ids),
                    "created_at": str(created_at),
                    "updated_at": str(updated_at),
                }
            )

        return result

    def upsert_preset(
        self,
        telegram_user_id: int,
        name: str,
        k_type: int,
        signal_ids: list[str],
        filter_ids: list[str],
    ) -> None:
        clean_name = name.strip()

        if not clean_name:
            raise ValueError("Имя пресета пустое")

        if len(signal_ids) == 0:
            raise ValueError("Нужно выбрать хотя бы один сигнал")

        # enforce limit
        presets = self.list_presets(telegram_user_id)
        if len(presets) >= MAX_PRESETS_PER_USER and all(p["name"] != clean_name for p in presets):
            raise ValueError("Достигнут лимит пресетов (3). Удалите один из существующих.")

        payload = (
            telegram_user_id,
            clean_name,
            int(k_type),
            json.dumps(signal_ids),
            json.dumps(filter_ids),
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_signal_presets (
                    telegram_user_id, name, k_type, signal_ids, filter_ids, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_user_id, name) DO UPDATE SET
                    k_type = excluded.k_type,
                    signal_ids = excluded.signal_ids,
                    filter_ids = excluded.filter_ids,
                    updated_at = CURRENT_TIMESTAMP
                """,
                payload,
            )
            connection.commit()

    def delete_preset(self, telegram_user_id: int, name: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM user_signal_presets
                WHERE telegram_user_id = ? AND name = ?
                """,
                (telegram_user_id, name.strip()),
            )
            connection.commit()

    def get_by_id(self, telegram_user_id: int, preset_id: int) -> dict | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT id, name, k_type, signal_ids, filter_ids, created_at, updated_at
                FROM user_signal_presets
                WHERE telegram_user_id = ? AND id = ?
                """,
                (telegram_user_id, preset_id),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        preset_id, name, k_type, signal_ids, filter_ids, created_at, updated_at = row
        return {
            "id": int(preset_id),
            "name": str(name),
            "k_type": int(k_type),
            "signal_ids": json.loads(signal_ids),
            "filter_ids": json.loads(filter_ids),
            "created_at": str(created_at),
            "updated_at": str(updated_at),
        }
