import uuid


class PaymentNotFoundError(Exception):
    """Платеж не найден."""

    def __init__(self, payment_id: uuid.UUID) -> None:
        super().__init__(f'Payment with id {payment_id} was not found.')


class IdempotencyKeyConflictError(Exception):
    """Idempotency key уже использован с отличающимся payload."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            f'Idempotency key "{idempotency_key}" is already used with a different payload.',
        )
