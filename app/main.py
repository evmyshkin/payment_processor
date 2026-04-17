from contextlib import asynccontextmanager
from typing import Any

import uvicorn

from fastapi import FastAPI
from starlette_exporter import PrometheusMiddleware

from app.api.error_handlers import register_exception_handlers
from app.api.router import router as main_router
from app.config import config
from app.utils.logger_setup import LoggerSetup


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Запуск логгера.

    Args:
        app: Экземпляр FastAPI приложения

    Yields:
        None: Контекст менеджер для жизненного цикла приложения
        :type app: FastAPI
    """
    # Запуск логгера
    LoggerSetup.configure_logging()

    try:
        yield
    finally:
        pass


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
