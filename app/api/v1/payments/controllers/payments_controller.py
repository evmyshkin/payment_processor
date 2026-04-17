import uuid

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import status

from app.api.dependencies.services import get_payments_service
from app.api.v1.payments.schemas import CreatePaymentRequestSchema
from app.api.v1.payments.schemas import CreatePaymentResponseSchema
from app.api.v1.payments.schemas import PaymentDetailsResponseSchema
from app.api.v1.payments.services import PaymentsService

router = APIRouter()


@router.post(
    '',
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreatePaymentResponseSchema,
)
async def create_payment(
    request: CreatePaymentRequestSchema,
    idempotency_key: Annotated[str, Header(alias='Idempotency-Key')],
    service: Annotated[PaymentsService, Depends(get_payments_service)],
) -> CreatePaymentResponseSchema:
    """Создает платеж."""
    return await service.create_payment(request=request, idempotency_key=idempotency_key)


@router.get(
    '/{payment_id}',
    response_model=PaymentDetailsResponseSchema,
)
async def get_payment(
    payment_id: uuid.UUID,
    service: Annotated[PaymentsService, Depends(get_payments_service)],
) -> PaymentDetailsResponseSchema:
    """Возвращает информацию о платеже."""
    return await service.get_payment(payment_id=payment_id)
