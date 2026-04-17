import uuid

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.outbox_event import OutboxEvent


class OutboxEventDAO:
    """DAO для работы с таблицей outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        aggregate_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> OutboxEvent:
        """Создает outbox-событие в текущей транзакции."""
        event = OutboxEvent(
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(event)
        await self._session.flush()
        return event
