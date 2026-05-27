from telegram import Update
from telegram.ext import Application

from internal.telegram.bot_factory import build_application


def init(default_filter_keys: frozenset[str] | None = None) -> Application:
    return build_application(default_filter_keys)


def run_bot() -> None:
    application = init()

    application.run_polling(
        allowed_updates=[Update.MESSAGE],
        drop_pending_updates=True,
    )
