from config import settings


def get_api_bot_key() -> str:
    return settings.API_BOT_KEY


print(get_api_bot_key())
