import asyncio

from collections.abc import Awaitable
from collections.abc import Callable
from typing import Any

import httpx

from loguru import logger

type WebhookPostFunc = Callable[[str, dict[str, Any], float], Awaitable[None]]


class WebhookDeliveryError(Exception):
    """Ошибка доставки webhook после всех попыток."""


async def _default_post(url: str, payload: dict[str, Any], timeout_seconds: float) -> None:
    """Отправляет webhook HTTP POST запрос."""
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        response = await client.post(url=url, json=payload)
        response.raise_for_status()


class WebhookSender:
    """Отправляет webhook с retry и экспоненциальной задержкой."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_attempts: int,
        retry_backoff_base_seconds: float,
        post_func: WebhookPostFunc | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max(max_attempts, 1)
        self._retry_backoff_base_seconds = max(retry_backoff_base_seconds, 0.0)
        self._post_func = post_func or _default_post
        self._sleep_func = sleep_func or asyncio.sleep

    async def send_with_retry(self, *, webhook_url: str, payload: dict[str, Any]) -> None:
        """Отправляет webhook с повторными попытками."""
        for attempt in range(1, self._max_attempts + 1):
            try:
                await self._post_func(webhook_url, payload, self._timeout_seconds)
                return
            except Exception as exc:
                logger.warning(
                    'Webhook attempt failed for url={} attempt={}/{} error={}',
                    webhook_url,
                    attempt,
                    self._max_attempts,
                    exc,
                )
                if attempt == self._max_attempts:
                    raise WebhookDeliveryError(
                        f'Webhook delivery failed after {self._max_attempts} attempts.',
                    ) from None

                delay = self._retry_backoff_base_seconds * (2 ** (attempt - 1))
                await self._sleep_func(delay)
