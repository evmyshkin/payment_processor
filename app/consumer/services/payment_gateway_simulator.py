import asyncio
import random
import uuid

from collections.abc import Awaitable
from collections.abc import Callable
from decimal import Decimal

from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum


class PaymentGatewaySimulator:
    """Эмулятор внешнего платежного шлюза."""

    def __init__(
        self,
        *,
        random_func: Callable[[], float] | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._random_func = random_func or random.random
        self._sleep_func = sleep_func or asyncio.sleep

    async def process_payment(
        self,
        *,
        payment_id: uuid.UUID,
        amount: Decimal,
        currency: CurrencyEnum,
    ) -> PaymentStatusEnum:
        """Обрабатывает платеж с задержкой 2-5 сек и вероятностью успеха 90%."""
        _ = (payment_id, amount, currency)
        delay = random.uniform(2.0, 5.0)
        await self._sleep_func(delay)

        if self._random_func() < 0.9:
            return PaymentStatusEnum.SUCCEEDED
        return PaymentStatusEnum.FAILED
