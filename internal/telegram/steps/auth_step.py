from telegram.ext import ContextTypes

from internal.telegram.auth import AuthService
from internal.telegram.steps.flow import AUTH_WAIT, SELECT_PAIR


def make_auth_handler(auth_service: AuthService):
    async def handle_auth(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_PAIR

        if not auth_service.has_tokens:
            await message.reply_text("Доступ запрещён. Токены не заданы.")
            return SELECT_PAIR

        user = update.effective_user

        if user is None:
            await message.reply_text("Доступ запрещён.")
            return SELECT_PAIR

        await message.reply_text("🔑 Введите токен доступа одним сообщением.")
        return AUTH_WAIT

    return handle_auth


def make_auth_wait_handler(auth_service: AuthService):
    async def handle_wait(update, context: ContextTypes.DEFAULT_TYPE) -> int:
        message = update.message

        if message is None:
            return SELECT_PAIR

        if not auth_service.has_tokens:
            await message.reply_text("🚫 Доступ запрещён. Токены не заданы.")
            return SELECT_PAIR

        user = update.effective_user
        if user is None:
            await message.reply_text("🚫 Доступ запрещён.")
            return SELECT_PAIR

        token = message.text.strip()

        if auth_service.authorize_with_token(int(user.id), token):
            await message.reply_text("✅ Авторизация успешна.")
        else:
            await message.reply_text("🚫 Доступ запрещён.")

        return SELECT_PAIR

    return handle_wait
