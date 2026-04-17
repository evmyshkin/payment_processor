from typing import Any
from typing import Protocol


class OutboxPublishError(Exception):
    """Ошибка публикации outbox-события в брокер."""


class OutboxPublisher(Protocol):
    """Контракт публикации outbox-события в брокер."""

    async def publish(self, *, event_type: str, payload: dict[str, Any]) -> None:
        """Публикует одно outbox-событие в брокер."""
