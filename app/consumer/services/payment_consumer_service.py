from datetime import UTC
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.consumer.schemas import PaymentCreatedEventSchema
from app.consumer.schemas import WebhookPayloadSchema
from app.consumer.services.payment_gateway_simulator import PaymentGatewaySimulator
from app.consumer.services.webhook_sender import WebhookSender
from app.db.dao.payment_dao import PaymentDAO
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.db.models.payment import Payment


class PaymentProcessingError(Exception):
    """Ошибка обработки входящего платежного события."""


class PaymentConsumerService:
    """Сервис обработки события payments.new."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        payment_dao: PaymentDAO,
        payment_gateway: PaymentGatewaySimulator,
        webhook_sender: WebhookSender,
    ) -> None:
        self._session = session
        self._payment_dao = payment_dao
        self._payment_gateway = payment_gateway
        self._webhook_sender = webhook_sender

    async def process(self, *, event: PaymentCreatedEventSchema) -> None:
        """Обрабатывает событие, обновляет статус и отправляет webhook."""
        payment = await self._payment_dao.get_by_id(payment_id=event.payment_id)
        if payment is None:
            raise PaymentProcessingError(f'Payment {event.payment_id} not found.')

        if self._is_pending(payment):
            try:
                status = await self._payment_gateway.process_payment(
                    payment_id=payment.id,
                    amount=payment.amount,
                    currency=payment.currency,
                )
                await self._payment_dao.mark_processed(
                    payment=payment,
                    status=status,
                    processed_at=datetime.now(tz=UTC),
                )
                await self._session.commit()
                await self._session.refresh(payment)
            except Exception:
                await self._session.rollback()
                raise

        payload = self._build_webhook_payload(payment=payment)
        await self._webhook_sender.send_with_retry(
            webhook_url=payment.webhook_url,
            payload=payload,
        )

    @staticmethod
    def _is_pending(payment: Payment) -> bool:
        return payment.status == PaymentStatusEnum.PENDING or payment.processed_at is None

    @staticmethod
    def _build_webhook_payload(payment: Payment) -> dict[str, str]:
        payload = WebhookPayloadSchema(
            payment_id=str(payment.id),
            status=payment.status.value,
            amount=str(payment.amount),
            currency=payment.currency.value,
            processed_at=payment.processed_at.isoformat() if payment.processed_at else '',
            idempotency_key=payment.idempotency_key,
        )
        return payload.model_dump()
