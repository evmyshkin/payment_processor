import uuid

from datetime import UTC
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.payments.services.outbox_dispatcher_service import OutboxDispatcherService
from app.broker.outbox_publisher import OutboxPublishError
from app.db.models.outbox_event import OutboxEvent


def _build_outbox_event() -> OutboxEvent:
    return OutboxEvent(
        id=uuid.uuid4(),
        aggregate_id=uuid.uuid4(),
        event_type='payments.new',
        payload={'payment_id': str(uuid.uuid4())},
        attempts=0,
        created_at=datetime.now(tz=UTC),
        published_at=None,
    )


@pytest.mark.asyncio
async def test_dispatch_batch_publishes_all_events() -> None:
    events = [_build_outbox_event(), _build_outbox_event()]
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    outbox_event_dao = Mock()
    outbox_event_dao.list_unpublished_for_update = AsyncMock(return_value=events)
    outbox_event_dao.mark_as_published = AsyncMock()
    outbox_event_dao.increment_attempts = AsyncMock()
    publisher = Mock()
    publisher.publish = AsyncMock()
    service = OutboxDispatcherService(
        session=session,
        outbox_event_dao=outbox_event_dao,
        publisher=publisher,
    )

    result = await service.dispatch_batch(batch_size=100)

    assert result.total_count == 2
    assert result.published_count == 2
    assert result.failed_count == 0
    outbox_event_dao.list_unpublished_for_update.assert_awaited_once_with(limit=100)
    assert publisher.publish.await_count == 2
    assert outbox_event_dao.mark_as_published.await_count == 2
    outbox_event_dao.increment_attempts.assert_not_awaited()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_batch_increments_attempts_on_publish_error() -> None:
    first_event = _build_outbox_event()
    second_event = _build_outbox_event()
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    outbox_event_dao = Mock()
    outbox_event_dao.list_unpublished_for_update = AsyncMock(return_value=[first_event, second_event])
    outbox_event_dao.mark_as_published = AsyncMock()
    outbox_event_dao.increment_attempts = AsyncMock()
    publisher = Mock()
    publisher.publish = AsyncMock(side_effect=[None, OutboxPublishError('publish error')])
    service = OutboxDispatcherService(
        session=session,
        outbox_event_dao=outbox_event_dao,
        publisher=publisher,
    )

    result = await service.dispatch_batch(batch_size=10)

    assert result.total_count == 2
    assert result.published_count == 1
    assert result.failed_count == 1
    outbox_event_dao.mark_as_published.assert_awaited_once_with(event=first_event)
    outbox_event_dao.increment_attempts.assert_awaited_once_with(event=second_event)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_batch_rollbacks_on_unhandled_error() -> None:
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    outbox_event_dao = Mock()
    outbox_event_dao.list_unpublished_for_update = AsyncMock(side_effect=SQLAlchemyError('db error'))
    publisher = Mock()
    publisher.publish = AsyncMock()
    service = OutboxDispatcherService(
        session=session,
        outbox_event_dao=outbox_event_dao,
        publisher=publisher,
    )

    with pytest.raises(SQLAlchemyError, match='db error'):
        await service.dispatch_batch(batch_size=100)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()
