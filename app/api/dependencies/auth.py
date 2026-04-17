from typing import Annotated

from fastapi import Header
from fastapi import HTTPException
from fastapi import status

from app.config import config


def require_api_key(
    x_api_key: Annotated[str | None, Header(alias='X-API-Key')] = None,
) -> None:
    """Проверяет API ключ для доступа к API."""
    if x_api_key is None or x_api_key != config.auth.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid API key.',
        )
