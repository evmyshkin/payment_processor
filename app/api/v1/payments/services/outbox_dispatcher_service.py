from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.broker.outbox_publisher import OutboxPublisher
from app.db.dao.outbox_event_dao import OutboxEventDAO


@dataclass(frozen=True, slots=True)
class OutboxDispatchResult:
    """Итог одной итерации отправки outbox-событий."""

    total_count: int
    published_count: int
    failed_count: int


class OutboxDispatcherService:
    """Сервис публикации outbox-событий в брокер сообщений."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        outbox_event_dao: OutboxEventDAO,
        publisher: OutboxPublisher,
    ) -> None:
        self._session = session
        self._outbox_event_dao = outbox_event_dao
        self._publisher = publisher

    async def dispatch_batch(self, *, batch_size: int) -> OutboxDispatchResult:
        """Публикует батч событий и обновляет outbox-состояние в БД."""
        try:
            events = await self._outbox_event_dao.list_unpublished_for_update(limit=batch_size)

            published_count = 0
            failed_count = 0
            for event in events:
                try:
                    await self._publisher.publish(
                        event_type=event.event_type,
                        payload=event.payload,
                    )
                    await self._outbox_event_dao.mark_as_published(event=event)
                    published_count += 1
                except Exception:
                    await self._outbox_event_dao.increment_attempts(event=event)
                    failed_count += 1

            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        return OutboxDispatchResult(
            total_count=len(events),
            published_count=published_count,
            failed_count=failed_count,
        )


class OutboxDispatcher:
    """Обертка над сервисом отправки outbox, создающая session на итерацию."""

    def __init__(
        self,
        *,
        session_maker: async_sessionmaker[AsyncSession],
        publisher: OutboxPublisher,
        batch_size: int,
    ) -> None:
        self._session_maker = session_maker
        self._publisher = publisher
        self._batch_size = batch_size

    async def dispatch_once(self) -> OutboxDispatchResult:
        """Выполняет одну итерацию отправки outbox-событий."""
        async with self._session_maker() as session:
            service = OutboxDispatcherService(
                session=session,
                outbox_event_dao=OutboxEventDAO(session=session),
                publisher=self._publisher,
            )
            return await service.dispatch_batch(batch_size=self._batch_size)
