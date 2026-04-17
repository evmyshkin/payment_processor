import logging

from datetime import UTC
from datetime import datetime

import orjson

from app.utils.logger_setup import InterceptHandler
from app.utils.logger_setup import LoggerSetup


class _FakeLevel:
    def __init__(self, *, name: str, no: int) -> None:
        self.name = name
        self.no = no


def test_serialize_extra_maps_numeric_level_to_name() -> None:
    record = {
        'level': _FakeLevel(name='Level 20', no=20),
        'message': 'test-message',
        'time': datetime.now(tz=UTC),
        'exception': None,
    }

    payload = LoggerSetup.serialize_extra(record=record)  # type: ignore[arg-type]
    parsed = orjson.loads(payload)

    assert parsed['level'] == 'INFO'
    assert parsed['message'] == 'test-message'


def test_configure_logging_installs_uvicorn_intercept_handlers() -> None:
    LoggerSetup.configure_logging()

    uvicorn_access_handlers = logging.getLogger('uvicorn.access').handlers
    uvicorn_error_handlers = logging.getLogger('uvicorn.error').handlers

    assert uvicorn_access_handlers
    assert uvicorn_error_handlers
    assert isinstance(uvicorn_access_handlers[0], InterceptHandler)
    assert isinstance(uvicorn_error_handlers[0], InterceptHandler)
