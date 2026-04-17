import logging
import sys

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import orjson

from loguru import logger

from app.config import config

if TYPE_CHECKING:
    from loguru import Record


class InterceptHandler(logging.Handler):
    """Переадресует stdlib-логи в loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Отправляет запись stdlib-логгера в loguru."""
        level_name = record.levelname
        if level_name.startswith('Level '):
            level_name = logging.getLevelName(record.levelno)

        logger.opt(exception=record.exc_info).log(level_name, record.getMessage())


class LoggerSetup:
    @staticmethod
    def serialize_extra(record: Record) -> str:
        """Сериализуем дополнительную информацию лога.

        Args:
            record: Record - запись лога.

        Returns:
            str - отформатированный вывод.
        """
        _exc, _exc_value, _tb = record['exception'] or (None, None, None)

        level_name = record['level'].name
        if level_name.startswith('Level '):
            level_name = logging.getLevelName(record['level'].no)

        subset = {
            'level': level_name,
            'message': record['message'],
            'datetime_utc': datetime.now(tz=UTC).strftime('%d.%m.%Y, %H:%M:%S'),
            'timestamp': record['time'].timestamp(),
        }

        return orjson.dumps(subset).decode('utf-8')

    @classmethod
    def format_logs(cls, record: Record) -> str:
        """Форматирование логов для продакшена.

        Args:
            record: Record - запись лога.

        Returns:
            str - отформатированный вывод.
        """

        record['extra']['serialized'] = cls.serialize_extra(record)
        return '{extra[serialized]}\n'

    @staticmethod
    def configure_stdlib_logging() -> None:
        """Переопределяет stdlib-логгеры на loguru sink."""
        handler = InterceptHandler()
        root_logger = logging.getLogger()
        root_logger.handlers = [handler]
        root_logger.setLevel(config.common.log_level.value)

        for logger_name in ('uvicorn', 'uvicorn.error', 'uvicorn.access', 'fastapi'):
            target_logger = logging.getLogger(logger_name)
            target_logger.handlers = [handler]
            target_logger.propagate = False
            target_logger.setLevel(config.common.log_level.value)

    @classmethod
    def configure_logging(cls) -> None:
        """Настройка логирования."""

        logger.remove()
        logger.add(sys.stdout, format=cls.format_logs, level=config.common.log_level.value)
        cls.configure_stdlib_logging()
