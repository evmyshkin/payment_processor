import uuid

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from app.consumer.schemas import PaymentCreatedEventSchema
from app.consumer.services.payment_consumer_service import PaymentConsumerService
from app.consumer.services.payment_consumer_service import PaymentProcessingError
from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.db.models.payment import Payment


def _build_payment(**overrides: object) -> Payment:
    payment = Payment(
        id=uuid.uuid4(),
        amount=Decimal('100.00'),
        currency=CurrencyEnum.RUB,
        description='consumer-test',
        metadata_={},
        status=PaymentStatusEnum.PENDING,
        idempotency_key='idem-1',
        webhook_url='https://example.com/hook',
        created_at=datetime.now(tz=UTC),
        processed_at=None,
    )
    for key, value in overrides.items():
        setattr(payment, key, value)
    return payment


@pytest.mark.asyncio
async def test_process_new_payment_success() -> None:
    event = PaymentCreatedEventSchema(payment_id=uuid.uuid4(), idempotency_key='idem-1')
    payment = _build_payment(id=event.payment_id)
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=payment)
    payment_dao.mark_processed = AsyncMock()
    payment_gateway = Mock()
    payment_gateway.process_payment = AsyncMock(return_value=PaymentStatusEnum.SUCCEEDED)
    webhook_sender = Mock()
    webhook_sender.send_with_retry = AsyncMock()
    service = PaymentConsumerService(
        session=session,
        payment_dao=payment_dao,
        payment_gateway=payment_gateway,
        webhook_sender=webhook_sender,
    )

    await service.process(event=event)

    payment_gateway.process_payment.assert_awaited_once()
    payment_dao.mark_processed.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(payment)
    webhook_sender.send_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_new_payment_already_processed_sends_webhook_only() -> None:
    event = PaymentCreatedEventSchema(payment_id=uuid.uuid4(), idempotency_key='idem-1')
    payment = _build_payment(
        id=event.payment_id,
        status=PaymentStatusEnum.SUCCEEDED,
        processed_at=datetime.now(tz=UTC),
    )
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=payment)
    payment_dao.mark_processed = AsyncMock()
    payment_gateway = Mock()
    payment_gateway.process_payment = AsyncMock()
    webhook_sender = Mock()
    webhook_sender.send_with_retry = AsyncMock()
    service = PaymentConsumerService(
        session=session,
        payment_dao=payment_dao,
        payment_gateway=payment_gateway,
        webhook_sender=webhook_sender,
    )

    await service.process(event=event)

    payment_gateway.process_payment.assert_not_awaited()
    payment_dao.mark_processed.assert_not_awaited()
    session.commit.assert_not_called()
    webhook_sender.send_with_retry.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_new_payment_not_found() -> None:
    event = PaymentCreatedEventSchema(payment_id=uuid.uuid4(), idempotency_key='idem-1')
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=None)
    payment_dao.mark_processed = AsyncMock()
    payment_gateway = Mock()
    payment_gateway.process_payment = AsyncMock()
    webhook_sender = Mock()
    webhook_sender.send_with_retry = AsyncMock()
    service = PaymentConsumerService(
        session=session,
        payment_dao=payment_dao,
        payment_gateway=payment_gateway,
        webhook_sender=webhook_sender,
    )

    with pytest.raises(PaymentProcessingError):
        await service.process(event=event)

    payment_gateway.process_payment.assert_not_awaited()
    webhook_sender.send_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_new_payment_rollbacks_on_gateway_error() -> None:
    event = PaymentCreatedEventSchema(payment_id=uuid.uuid4(), idempotency_key='idem-1')
    payment = _build_payment(id=event.payment_id)
    session = Mock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=payment)
    payment_dao.mark_processed = AsyncMock()
    payment_gateway = Mock()
    payment_gateway.process_payment = AsyncMock(side_effect=RuntimeError('gateway down'))
    webhook_sender = Mock()
    webhook_sender.send_with_retry = AsyncMock()
    service = PaymentConsumerService(
        session=session,
        payment_dao=payment_dao,
        payment_gateway=payment_gateway,
        webhook_sender=webhook_sender,
    )

    with pytest.raises(RuntimeError):
        await service.process(event=event)

    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()
    webhook_sender.send_with_retry.assert_not_awaited()


@pytest.mark.asyncio
async def test_build_webhook_payload_matches_schema_contract() -> None:
    processed_at = datetime.now(tz=UTC)
    payment = _build_payment(
        status=PaymentStatusEnum.SUCCEEDED,
        processed_at=processed_at,
    )

    payload = PaymentConsumerService._build_webhook_payload(payment=payment)

    assert payload == {
        'payment_id': str(payment.id),
        'status': 'succeeded',
        'amount': '100.00',
        'currency': 'RUB',
        'processed_at': processed_at.isoformat(),
        'idempotency_key': 'idem-1',
    }
