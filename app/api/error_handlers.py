from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status

from app.api.v1.payments.services.exceptions import IdempotencyKeyConflictError
from app.api.v1.payments.services.exceptions import PaymentNotFoundError


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики доменных исключений API."""

    @app.exception_handler(PaymentNotFoundError)
    async def handle_payment_not_found(
        request: Request,
        exc: PaymentNotFoundError,
    ) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={'detail': str(exc)},
        )

    @app.exception_handler(IdempotencyKeyConflictError)
    async def handle_idempotency_conflict(
        request: Request,
        exc: IdempotencyKeyConflictError,
    ) -> JSONResponse:
        _ = request
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={'detail': str(exc)},
        )
