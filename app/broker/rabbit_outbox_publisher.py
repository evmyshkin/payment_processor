from typing import Any

from faststream.rabbit import ExchangeType
from faststream.rabbit import RabbitBroker
from faststream.rabbit import RabbitExchange

from app.broker.outbox_publisher import OutboxPublisher


class RabbitOutboxPublisher(OutboxPublisher):
    """Публикует outbox-события в RabbitMQ через FastStream."""

    def __init__(
        self,
        *,
        broker: RabbitBroker,
        exchange_name: str,
    ) -> None:
        self._broker = broker
        self._exchange = RabbitExchange(
            name=exchange_name,
            type=ExchangeType.DIRECT,
            durable=True,
        )

    async def publish(self, *, event_type: str, payload: dict[str, Any]) -> None:
        """Отправляет сообщение в exchange с routing key равным типу события."""
        await self._broker.publish(
            message=payload,
            exchange=self._exchange,
            routing_key=event_type,
            persist=True,
            message_type=event_type,
        )
