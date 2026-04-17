from app.config import config
from app.consumer.main import PAYMENTS_NEW_QUEUE
from app.consumer.main import app
from app.consumer.main import setup_topology


def test_consumer_app_exists() -> None:
    assert app is not None


def test_main_queue_has_dlq_delivery_limit() -> None:
    assert PAYMENTS_NEW_QUEUE.arguments is not None
    assert PAYMENTS_NEW_QUEUE.arguments['x-delivery-limit'] == config.rabbit.new_payments_delivery_limit
    assert PAYMENTS_NEW_QUEUE.arguments['x-dead-letter-exchange'] == config.rabbit.dead_letter_exchange_name
    assert PAYMENTS_NEW_QUEUE.arguments['x-dead-letter-routing-key'] == config.rabbit.dead_letter_routing_key


def test_topology_setup_registered_after_broker_start() -> None:
    assert any(getattr(hook, '__name__', '') == setup_topology.__name__ for hook in app._after_startup_calling)
