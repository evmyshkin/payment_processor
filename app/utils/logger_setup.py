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


class LoggerSetup:
    @staticmethod
    def serialize_extra(record: 'Record') -> str:
        """Сериализуем дополнительную информацию лога.

        Args:
            record: Record - запись лога.

        Returns:
            str - отформатированный вывод.
        """
        _exc, _exc_value, _tb = record['exception'] or (None, None, None)

        subset = {
            'level': record['level'].name,
            'message': record['message'],
            'datetime_utc': datetime.now(tz=UTC).strftime('%d.%m.%Y, %H:%M:%S'),
            'timestamp': record['time'].timestamp(),
        }

        return orjson.dumps(subset).decode('utf-8')

    @classmethod
    def format_logs(cls, record: 'Record') -> str:
        """Форматирование логов для продакшена.

        Args:
            record: Record - запись лога.

        Returns:
            str - отформатированный вывод.
        """

        record['extra']['serialized'] = cls.serialize_extra(record)
        return '{extra[serialized]}\n'

    @staticmethod
    def disable_uvicorn_logging() -> None:
        """Отключает стандартные логеры Uvicorn."""
        logging.getLogger('uvicorn.access').handlers = []
        logging.getLogger('uvicorn.error').handlers = []

    @classmethod
    def configure_logging(cls) -> None:
        """Настройка логирования."""

        logger.remove()
        logger.add(sys.stdout, format=cls.format_logs, level=config.common.log_level.value)
        # cls.disable_uvicorn_logging()
