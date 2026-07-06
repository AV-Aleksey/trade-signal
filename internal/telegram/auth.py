from __future__ import annotations

from internal.storage.user_auth_repository import UserAuthRepository


class AuthService:
    def __init__(self, allowed_tokens: list[str], repo: UserAuthRepository) -> None:
        self._allowed = {t.strip() for t in allowed_tokens if t.strip()}
        self._repo = repo

    def is_authorized(self, telegram_user_id: int) -> bool:
        return self._repo.is_authorized(telegram_user_id)

    def authorize_with_token(self, telegram_user_id: int, token: str) -> bool:
        if token.strip() in self._allowed:
            self._repo.authorize(telegram_user_id)
            return True
        return False

    @property
    def has_tokens(self) -> bool:
        return bool(self._allowed)
