import uuid

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.payments.schemas import CreatePaymentRequestSchema
from app.api.v1.payments.services.exceptions import IdempotencyKeyConflictError
from app.api.v1.payments.services.exceptions import PaymentNotFoundError
from app.api.v1.payments.services.payments_service import PaymentsService
from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.db.models.payment import Payment


def _build_payment(**overrides: object) -> Payment:
    payment = Payment(
        id=uuid.uuid4(),
        amount=Decimal('120.00'),
        currency=CurrencyEnum.RUB,
        description='test payment',
        metadata_={'order_id': '42'},
        status=PaymentStatusEnum.PENDING,
        idempotency_key='idem-42',
        webhook_url='https://example.com/webhook',
        created_at=datetime.now(tz=UTC),
        processed_at=None,
    )
    for key, value in overrides.items():
        setattr(payment, key, value)
    return payment


@pytest.mark.asyncio
async def test_create_payment_success() -> None:
    request = CreatePaymentRequestSchema(
        amount=Decimal('120.00'),
        currency=CurrencyEnum.RUB,
        description='test payment',
        metadata={'order_id': '42'},
        webhook_url='https://example.com/webhook',
    )
    payment = _build_payment()
    session = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_idempotency_key = AsyncMock(return_value=None)
    payment_dao.create = AsyncMock(return_value=payment)
    outbox_dao = Mock()
    outbox_dao.create = AsyncMock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    response = await service.create_payment(request=request, idempotency_key='idem-42')

    assert response.payment_id == payment.id
    assert response.status == PaymentStatusEnum.PENDING
    payment_dao.create.assert_awaited_once_with(
        amount=request.amount,
        currency=request.currency,
        description=request.description,
        metadata=request.metadata,
        idempotency_key='idem-42',
        webhook_url='https://example.com/webhook',
    )
    outbox_dao.create.assert_awaited_once_with(
        aggregate_id=payment.id,
        event_type='payments.new',
        payload={'payment_id': str(payment.id), 'idempotency_key': payment.idempotency_key},
    )
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(payment)
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_payment_idempotency_returns_existing_payment() -> None:
    request = CreatePaymentRequestSchema(
        amount=Decimal('120.00'),
        currency=CurrencyEnum.RUB,
        description='test payment',
        metadata={'order_id': '42'},
        webhook_url='https://example.com/webhook',
    )
    payment = _build_payment()
    session = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_idempotency_key = AsyncMock(return_value=payment)
    payment_dao.create = AsyncMock()
    outbox_dao = Mock()
    outbox_dao.create = AsyncMock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    response = await service.create_payment(request=request, idempotency_key='idem-42')

    assert response.payment_id == payment.id
    payment_dao.create.assert_not_called()
    outbox_dao.create.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_create_payment_idempotency_conflict() -> None:
    request = CreatePaymentRequestSchema(
        amount=Decimal('120.00'),
        currency=CurrencyEnum.RUB,
        description='test payment',
        metadata={'order_id': '42'},
        webhook_url='https://example.com/webhook',
    )
    payment = _build_payment(amount=Decimal('130.00'))
    session = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_idempotency_key = AsyncMock(return_value=payment)
    payment_dao.create = AsyncMock()
    outbox_dao = Mock()
    outbox_dao.create = AsyncMock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    with pytest.raises(IdempotencyKeyConflictError):
        await service.create_payment(request=request, idempotency_key='idem-42')

    payment_dao.create.assert_not_called()
    outbox_dao.create.assert_not_called()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_payment_success() -> None:
    payment = _build_payment()
    session = Mock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=payment)
    outbox_dao = Mock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    response = await service.get_payment(payment_id=payment.id)

    assert response.payment_id == payment.id
    assert response.idempotency_key == payment.idempotency_key
    payment_dao.get_by_id.assert_awaited_once_with(payment_id=payment.id)


@pytest.mark.asyncio
async def test_get_payment_not_found() -> None:
    payment_id = uuid.uuid4()
    session = Mock()
    payment_dao = Mock()
    payment_dao.get_by_id = AsyncMock(return_value=None)
    outbox_dao = Mock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    with pytest.raises(PaymentNotFoundError):
        await service.get_payment(payment_id=payment_id)


@pytest.mark.asyncio
async def test_create_payment_rollbacks_on_sqlalchemy_error() -> None:
    request = CreatePaymentRequestSchema(
        amount=Decimal('120.00'),
        currency=CurrencyEnum.RUB,
        description='test payment',
        metadata={'order_id': '42'},
        webhook_url='https://example.com/webhook',
    )
    session = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    payment_dao = Mock()
    payment_dao.get_by_idempotency_key = AsyncMock(return_value=None)
    payment_dao.create = AsyncMock(side_effect=SQLAlchemyError('db error'))
    outbox_dao = Mock()
    outbox_dao.create = AsyncMock()
    service = PaymentsService(
        session=session,
        payment_dao=payment_dao,
        outbox_event_dao=outbox_dao,
    )

    with pytest.raises(SQLAlchemyError, match='db error'):
        await service.create_payment(request=request, idempotency_key='idem-42')

    session.rollback.assert_awaited_once()
    session.commit.assert_not_called()
    session.refresh.assert_not_called()
    outbox_dao.create.assert_not_called()
