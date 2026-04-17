import asyncio

from contextlib import asynccontextmanager
from contextlib import suppress
from typing import Any

import uvicorn

from aiormq.exceptions import AMQPError
from fastapi import FastAPI
from faststream.rabbit import RabbitBroker
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette_exporter import PrometheusMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.router import router as main_router
from app.api.v1.payments.services.outbox_dispatcher_service import OutboxDispatcher
from app.broker.rabbit_outbox_publisher import RabbitOutboxPublisher
from app.config import config
from app.db.session import get_session_maker
from app.utils.logger_setup import LoggerSetup

LoggerSetup.configure_logging()


async def run_outbox_dispatcher_loop(
    *,
    dispatcher: OutboxDispatcher,
    poll_interval_seconds: float,
) -> None:
    """Бесконечный цикл отправки outbox-событий."""
    while True:
        try:
            await dispatcher.dispatch_once()
        except asyncio.CancelledError:
            raise
        except SQLAlchemyError:
            logger.exception('Ошибка итерации диспетчера outbox.')

        await asyncio.sleep(max(poll_interval_seconds, 0.1))


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Запуск логгера.

    Args:
        app: Экземпляр FastAPI приложения

    Yields:
        None: Контекст менеджер для жизненного цикла приложения
        :type app: FastAPI
    """
    broker: RabbitBroker | None = None
    outbox_task: asyncio.Task[None] | None = None
    if config.outbox.enabled and config.db.is_configured():
        try:
            broker = RabbitBroker(config.get_rabbit_url())
            await broker.start()
            outbox_publisher = RabbitOutboxPublisher(
                broker=broker,
                exchange_name=config.rabbit.exchange_name,
            )
            outbox_dispatcher = OutboxDispatcher(
                session_maker=get_session_maker(),
                publisher=outbox_publisher,
                batch_size=config.outbox.batch_size,
            )
            outbox_task = asyncio.create_task(
                run_outbox_dispatcher_loop(
                    dispatcher=outbox_dispatcher,
                    poll_interval_seconds=config.outbox.poll_interval_seconds,
                ),
                name='outbox-dispatcher',
            )
        except AMQPError:
            logger.exception('Не удалось запустить диспетчер outbox.')
            broker = None
        except OSError:
            logger.exception('Не удалось запустить диспетчер outbox.')
            broker = None
    else:
        logger.warning(
            'Диспетчер outbox отключен: установите OUTBOX__ENABLED=true и задайте настройки БД для включения.'
        )

    try:
        yield
    finally:
        if outbox_task is not None:
            outbox_task.cancel()
            with suppress(asyncio.CancelledError):
                await outbox_task

        if broker is not None:
            await broker.close()


# Fastapi. Запускаем приложение.
fastapi_app = FastAPI(
    lifespan=lifespan,
    title='mock_api',
    description="""Микросервис для асинхронной обработки платежей. Пинимает запросы на оплату, обрабатывает их
    через внешний платежный щлюз и уведомляет клиента о результате через webhook.
    """,
)


# Prometheus. Запускаем экспорт метрик.
fastapi_app.add_middleware(
    PrometheusMiddleware,
    app_name=config.common.app_name,
    prefix='fast_api',
    skip_methods=['OPTIONS', 'HEAD'],
    skip_paths=config.common.disabled_log_endpoints,
)

register_exception_handlers(fastapi_app)
fastapi_app.include_router(main_router)


if __name__ == '__main__':
    uvicorn.run(fastapi_app, host='127.0.0.1', port=8000)
