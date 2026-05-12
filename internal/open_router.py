import time
from typing import Any

import requests

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-oss-20b:free"
DEFAULT_PROMPT = "привет как дела"

MAX_429_RETRIES = 6
BACKOFF_BASE_SEC = 3.0
BACKOFF_MAX_SEC = 90.0


class OpenRouterRateLimitError(Exception):
    pass


def _wait_after_429(response: requests.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After")
    if raw is not None:
        try:
            return min(float(raw), BACKOFF_MAX_SEC)
        except ValueError:
            pass
    return min(BACKOFF_BASE_SEC * (2**attempt), BACKOFF_MAX_SEC)


class OpenRouter:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key.strip()
        self.model = model

    def chat(
        self,
        user_content: str | None = None,
        *,
        system_content: str | None = None,
    ) -> str:
        text = (user_content or DEFAULT_PROMPT).strip()
        if not self.api_key:
            raise RuntimeError("Не задан OPEN_ROUTER_API_KEY")
        messages: list[dict[str, str]] = []

        if system_content:
            messages.append({"role": "system", "content": system_content.strip()})

        messages.append({"role": "user", "content": text})
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        for attempt in range(MAX_429_RETRIES):
            response = requests.post(
                OPENROUTER_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=120,
            )

            if response.status_code == 429:
                if attempt >= MAX_429_RETRIES - 1:
                    raise OpenRouterRateLimitError(
                        "Лимит запросов OpenRouter (429). Подожди 1–3 минуты "
                        "или попробуй позже; бесплатные модели режутся жёстче."
                    )
                delay = _wait_after_429(response, attempt)
                time.sleep(delay)
                continue

            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return str(data)
            msg = choices[0].get("message") or {}
            content = msg.get("content")
            if not content:
                return str(data)
            return str(content).strip()
