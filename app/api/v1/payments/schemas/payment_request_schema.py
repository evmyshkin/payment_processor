from decimal import Decimal
from typing import Any

from pydantic import AnyHttpUrl
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.db.enums.currency_enum import CurrencyEnum


class CreatePaymentRequestSchema(BaseModel):
    """Схема запроса создания платежа."""

    model_config = ConfigDict(extra='forbid')

    amount: Decimal = Field(gt=Decimal('0'), max_digits=18, decimal_places=2)
    currency: CurrencyEnum
    description: str = Field(min_length=1, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    webhook_url: AnyHttpUrl
