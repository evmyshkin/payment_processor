import uuid

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import Mock

import pytest

from app.api.v1.payments.controllers.payments_controller import create_payment
from app.api.v1.payments.controllers.payments_controller import get_payment
from app.api.v1.payments.schemas import CreatePaymentRequestSchema
from app.api.v1.payments.schemas import CreatePaymentResponseSchema
from app.api.v1.payments.schemas import PaymentDetailsResponseSchema
from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum


@pytest.mark.asyncio
async def test_create_payment_controller_delegates_to_service() -> None:
    payment_id = uuid.uuid4()
    request = CreatePaymentRequestSchema(
        amount=Decimal('10.00'),
        currency=CurrencyEnum.USD,
        description='controller-test',
        metadata={'a': 1},
        webhook_url='https://example.com/webhook',
    )
    response = CreatePaymentResponseSchema(
        payment_id=payment_id,
        status=PaymentStatusEnum.PENDING,
        created_at=datetime.now(tz=UTC),
    )
    service = Mock()
    service.create_payment = AsyncMock(return_value=response)

    result = await create_payment(request=request, idempotency_key='idem-1', service=service)

    assert result == response
    service.create_payment.assert_awaited_once_with(
        request=request,
        idempotency_key='idem-1',
    )


@pytest.mark.asyncio
async def test_get_payment_controller_delegates_to_service() -> None:
    payment_id = uuid.uuid4()
    response = PaymentDetailsResponseSchema(
        payment_id=payment_id,
        amount=Decimal('10.00'),
        currency=CurrencyEnum.USD,
        description='controller-test',
        metadata={'a': 1},
        status=PaymentStatusEnum.PENDING,
        idempotency_key='idem-1',
        webhook_url='https://example.com/webhook',
        created_at=datetime.now(tz=UTC),
        processed_at=None,
    )
    service = Mock()
    service.get_payment = AsyncMock(return_value=response)

    result = await get_payment(payment_id=payment_id, service=service)

    assert result == response
    service.get_payment.assert_awaited_once_with(payment_id=payment_id)
