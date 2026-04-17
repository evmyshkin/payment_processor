import uuid

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict

from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum


class CreatePaymentResponseSchema(BaseModel):
    """Схема ответа создания платежа."""

    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    status: PaymentStatusEnum
    created_at: datetime


class PaymentDetailsResponseSchema(BaseModel):
    """Схема детальной информации по платежу."""

    model_config = ConfigDict(from_attributes=True)

    payment_id: uuid.UUID
    amount: Decimal
    currency: CurrencyEnum
    description: str
    metadata: dict[str, Any]
    status: PaymentStatusEnum
    idempotency_key: str
    webhook_url: str
    created_at: datetime
    processed_at: datetime | None
