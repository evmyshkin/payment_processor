import uuid

from datetime import UTC
from datetime import datetime
from typing import Any

from sqlalchemy import select
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

    async def list_unpublished_for_update(self, *, limit: int) -> list[OutboxEvent]:
        """Возвращает батч непубликованных outbox-событий с блокировкой."""
        query = (
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None))
            .order_by(OutboxEvent.created_at.asc())
            .limit(max(limit, 1))
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def mark_as_published(
        self,
        *,
        event: OutboxEvent,
        published_at: datetime | None = None,
    ) -> None:
        """Помечает outbox-событие как опубликованное."""
        event.published_at = published_at or datetime.now(tz=UTC)
        await self._session.flush()

    async def increment_attempts(self, *, event: OutboxEvent) -> None:
        """Инкрементирует количество попыток публикации события."""
        event.attempts += 1
        await self._session.flush()
