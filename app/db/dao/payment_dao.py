import uuid

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.db.models.payment import Payment


class PaymentDAO:
    """DAO для работы с таблицей payments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment | None:
        """Возвращает платеж по его идентификатору."""
        query = select(Payment).where(Payment.id == payment_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment | None:
        """Возвращает платеж по ключу идемпотентности."""
        query = select(Payment).where(Payment.idempotency_key == idempotency_key)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        amount: Decimal,
        currency: CurrencyEnum,
        description: str,
        metadata: dict[str, Any],
        idempotency_key: str,
        webhook_url: str,
    ) -> Payment:
        """Создает новый платеж в текущей транзакции."""
        payment = Payment(
            amount=amount,
            currency=currency,
            description=description,
            metadata_=metadata,
            status=PaymentStatusEnum.PENDING,
            idempotency_key=idempotency_key,
            webhook_url=webhook_url,
        )
        self._session.add(payment)
        await self._session.flush()
        return payment
