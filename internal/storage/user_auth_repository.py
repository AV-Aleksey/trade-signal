from __future__ import annotations

import sqlite3
from pathlib import Path

from internal.config import settings


class UserAuthRepository:
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
                CREATE TABLE IF NOT EXISTS user_auth (
                    telegram_user_id INTEGER PRIMARY KEY,
                    authorized_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )
            connection.commit()

    def is_authorized(self, telegram_user_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "SELECT 1 FROM user_auth WHERE telegram_user_id = ? LIMIT 1",
                (telegram_user_id,),
            )
            return cursor.fetchone() is not None

    def authorize(self, telegram_user_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_auth (telegram_user_id, authorized_at)
                VALUES (?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    authorized_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id,),
            )
            connection.commit()
