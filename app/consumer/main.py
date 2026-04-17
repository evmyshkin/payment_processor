from faststream import FastStream
from faststream.middlewares import AckPolicy
from faststream.rabbit import ExchangeType
from faststream.rabbit import QueueType
from faststream.rabbit import RabbitBroker
from faststream.rabbit import RabbitExchange
from faststream.rabbit import RabbitQueue
from loguru import logger

from app.config import config
from app.consumer.schemas import PaymentCreatedEventSchema
from app.consumer.services import PaymentConsumerService
from app.consumer.services import PaymentGatewaySimulator
from app.consumer.services import WebhookDeliveryError
from app.consumer.services import WebhookSender
from app.db.dao.payment_dao import PaymentDAO
from app.db.session import get_session_maker
from app.utils.logger_setup import LoggerSetup

LoggerSetup.configure_logging()

broker = RabbitBroker(config.get_rabbit_url(), logger=logger)

PAYMENTS_EXCHANGE = RabbitExchange(
    name=config.rabbit.exchange_name,
    type=ExchangeType.DIRECT,
    durable=True,
)
DLQ_EXCHANGE = RabbitExchange(
    name=config.rabbit.dead_letter_exchange_name,
    type=ExchangeType.DIRECT,
    durable=True,
)
PAYMENTS_NEW_QUEUE = RabbitQueue(
    name=config.rabbit.new_payments_queue_name,
    queue_type=QueueType.QUORUM,
    durable=True,
    routing_key=config.rabbit.new_payments_routing_key,
    arguments={
        'x-delivery-limit': config.rabbit.new_payments_delivery_limit,
        'x-dead-letter-exchange': config.rabbit.dead_letter_exchange_name,
        'x-dead-letter-routing-key': config.rabbit.dead_letter_routing_key,
    },
)
PAYMENTS_DLQ_QUEUE = RabbitQueue(
    name=config.rabbit.dead_letter_queue_name,
    queue_type=QueueType.QUORUM,
    durable=True,
)

gateway_simulator = PaymentGatewaySimulator()
webhook_sender = WebhookSender(
    timeout_seconds=config.webhook.timeout_seconds,
    max_attempts=config.webhook.max_attempts,
    retry_backoff_base_seconds=config.webhook.retry_backoff_base_seconds,
)


async def setup_topology() -> None:
    """Создает DLQ exchange/queue и binding."""
    dlq_exchange = await broker.declare_exchange(DLQ_EXCHANGE)
    dlq_queue = await broker.declare_queue(PAYMENTS_DLQ_QUEUE)
    await dlq_queue.bind(dlq_exchange, routing_key=config.rabbit.dead_letter_routing_key)


app = FastStream(
    broker,
    logger=logger,
    after_startup=[setup_topology],
)


@broker.subscriber(
    queue=PAYMENTS_NEW_QUEUE,
    exchange=PAYMENTS_EXCHANGE,
    ack_policy=AckPolicy.NACK_ON_ERROR,
)
async def process_new_payment(event: PaymentCreatedEventSchema) -> None:
    """Обрабатывает входящее событие создания платежа."""
    async with get_session_maker()() as session:
        service = PaymentConsumerService(
            session=session,
            payment_dao=PaymentDAO(session=session),
            payment_gateway=gateway_simulator,
            webhook_sender=webhook_sender,
        )
        try:
            await service.process(event=event)
        except WebhookDeliveryError as exc:
            logger.error(
                'Не удалось доставить webhook для payment_id={} idempotency_key={}: {}',
                event.payment_id,
                event.idempotency_key,
                exc,
            )
            raise RuntimeError(str(exc)) from None
