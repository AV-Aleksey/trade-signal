from __future__ import annotations

import sqlite3
from pathlib import Path

from internal.config import settings
from internal.security.token_crypto import decrypt_token, encrypt_token


class ItickTokenRepository:
    def __init__(
        self,
        db_path: str | None = None,
        encryption_secret: str | None = None,
    ) -> None:
        self._db_path = Path(db_path or settings.SQLITE_DB_PATH).expanduser()
        self._encryption_secret = (encryption_secret or settings.TOKEN_ENCRYPTION_SECRET).strip()

        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_itick_tokens (
                    telegram_user_id INTEGER PRIMARY KEY,
                    token_ciphertext BLOB NOT NULL,
                    nonce BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """,
            )
            connection.commit()

    def update_itick_token(self, telegram_user_id: int, token: str | None) -> None:
        with self._connect() as connection:
            if token is None:
                connection.execute(
                    "DELETE FROM user_itick_tokens WHERE telegram_user_id = ?",
                    (telegram_user_id,),
                )
                connection.commit()

                return

            ciphertext, nonce, salt = encrypt_token(token, self._encryption_secret)
            connection.execute(
                """
                INSERT INTO user_itick_tokens (
                    telegram_user_id,
                    token_ciphertext,
                    nonce,
                    salt,
                    updated_at
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    token_ciphertext = excluded.token_ciphertext,
                    nonce = excluded.nonce,
                    salt = excluded.salt,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (telegram_user_id, ciphertext, nonce, salt),
            )
            connection.commit()

    def get_itick_token(self, telegram_user_id: int) -> str | None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT token_ciphertext, nonce, salt
                FROM user_itick_tokens
                WHERE telegram_user_id = ?
                """,
                (telegram_user_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        ciphertext, nonce, salt = row

        return decrypt_token(ciphertext, nonce, salt, self._encryption_secret)
