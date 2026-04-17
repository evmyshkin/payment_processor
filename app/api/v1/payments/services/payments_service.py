import uuid

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.payments.schemas import CreatePaymentRequestSchema
from app.api.v1.payments.schemas import CreatePaymentResponseSchema
from app.api.v1.payments.schemas import PaymentDetailsResponseSchema
from app.api.v1.payments.services.exceptions import IdempotencyKeyConflictError
from app.api.v1.payments.services.exceptions import PaymentNotFoundError
from app.db.dao import OutboxEventDAO
from app.db.dao import PaymentDAO
from app.db.models.payment import Payment


class PaymentsService:
    """Сервис прикладной логики платежей."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        payment_dao: PaymentDAO,
        outbox_event_dao: OutboxEventDAO,
    ) -> None:
        self._session = session
        self._payment_dao = payment_dao
        self._outbox_event_dao = outbox_event_dao

    async def create_payment(
        self,
        *,
        request: CreatePaymentRequestSchema,
        idempotency_key: str,
    ) -> CreatePaymentResponseSchema:
        """Создает платеж и outbox-событие либо возвращает существующий платеж."""
        existing_payment = await self._payment_dao.get_by_idempotency_key(idempotency_key=idempotency_key)
        if existing_payment is not None:
            if not self._is_same_request(existing_payment=existing_payment, request=request):
                raise IdempotencyKeyConflictError(idempotency_key=idempotency_key)

            return self._to_create_response(existing_payment)

        try:
            payment = await self._payment_dao.create(
                amount=request.amount,
                currency=request.currency,
                description=request.description,
                metadata=request.metadata,
                idempotency_key=idempotency_key,
                webhook_url=str(request.webhook_url),
            )
            await self._outbox_event_dao.create(
                aggregate_id=payment.id,
                event_type='payments.new',
                payload=self._build_outbox_payload(payment=payment),
            )
            await self._session.commit()
            await self._session.refresh(payment)
        except Exception:
            await self._session.rollback()
            raise

        return self._to_create_response(payment)

    async def get_payment(self, *, payment_id: uuid.UUID) -> PaymentDetailsResponseSchema:
        """Возвращает детальную информацию о платеже."""
        payment = await self._payment_dao.get_by_id(payment_id=payment_id)
        if payment is None:
            raise PaymentNotFoundError(payment_id=payment_id)

        return self._to_details_response(payment)

    @staticmethod
    def _to_create_response(payment: Payment) -> CreatePaymentResponseSchema:
        return CreatePaymentResponseSchema(
            payment_id=payment.id,
            status=payment.status,
            created_at=payment.created_at,
        )

    @staticmethod
    def _to_details_response(payment: Payment) -> PaymentDetailsResponseSchema:
        return PaymentDetailsResponseSchema(
            payment_id=payment.id,
            amount=payment.amount,
            currency=payment.currency,
            description=payment.description,
            metadata=payment.metadata_,
            status=payment.status,
            idempotency_key=payment.idempotency_key,
            webhook_url=payment.webhook_url,
            created_at=payment.created_at,
            processed_at=payment.processed_at,
        )

    @staticmethod
    def _build_outbox_payload(payment: Payment) -> dict[str, str]:
        return {
            'payment_id': str(payment.id),
            'idempotency_key': payment.idempotency_key,
        }

    @staticmethod
    def _is_same_request(
        *,
        existing_payment: Payment,
        request: CreatePaymentRequestSchema,
    ) -> bool:
        return (
            existing_payment.amount == request.amount.quantize(Decimal('0.01'))
            and existing_payment.currency == request.currency
            and existing_payment.description == request.description
            and existing_payment.metadata_ == request.metadata
            and existing_payment.webhook_url == str(request.webhook_url)
        )
