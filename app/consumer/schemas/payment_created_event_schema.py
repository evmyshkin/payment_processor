import uuid

from pydantic import BaseModel
from pydantic import ConfigDict


class PaymentCreatedEventSchema(BaseModel):
    """Событие о создании платежа из outbox."""

    model_config = ConfigDict(extra='forbid')

    payment_id: uuid.UUID
    idempotency_key: str
