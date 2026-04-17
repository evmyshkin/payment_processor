from pydantic import BaseModel
from pydantic import ConfigDict


class WebhookPayloadSchema(BaseModel):
    """Схема webhook-уведомления о результате обработки платежа."""

    model_config = ConfigDict(extra='forbid')

    payment_id: str
    status: str
    amount: str
    currency: str
    processed_at: str
    idempotency_key: str
