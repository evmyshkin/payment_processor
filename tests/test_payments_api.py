import uuid

from datetime import UTC
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.api.dependencies.services import get_payments_service
from app.api.v1.payments.schemas import CreatePaymentResponseSchema
from app.api.v1.payments.schemas import PaymentDetailsResponseSchema
from app.api.v1.payments.services.exceptions import IdempotencyKeyConflictError
from app.api.v1.payments.services.exceptions import PaymentNotFoundError
from app.config import config
from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.main import fastapi_app


def test_api_key_is_required_for_all_endpoints() -> None:
    with TestClient(fastapi_app) as client:
        response = client.get('/health')

    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid API key.'}


def test_create_payment_api_success() -> None:
    payment_id = uuid.uuid4()
    mock_service = Mock()
    mock_service.create_payment = AsyncMock(
        return_value=CreatePaymentResponseSchema(
            payment_id=payment_id,
            status=PaymentStatusEnum.PENDING,
            created_at=datetime.now(tz=UTC),
        ),
    )
    fastapi_app.dependency_overrides[get_payments_service] = lambda: mock_service
    with TestClient(fastapi_app) as client:
        response = client.post(
            '/api/v1/payments',
            headers={
                'X-API-Key': config.auth.api_key,
                'Idempotency-Key': 'idem-123',
            },
            json={
                'amount': '10.00',
                'currency': 'USD',
                'description': 'api-test',
                'metadata': {'order_id': '1'},
                'webhook_url': 'https://example.com/hook',
            },
        )
    fastapi_app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json()['payment_id'] == str(payment_id)
    assert response.json()['status'] == 'pending'
    mock_service.create_payment.assert_awaited_once()


def test_create_payment_api_idempotency_conflict() -> None:
    mock_service = Mock()
    mock_service.create_payment = AsyncMock(
        side_effect=IdempotencyKeyConflictError(idempotency_key='idem-123'),
    )
    fastapi_app.dependency_overrides[get_payments_service] = lambda: mock_service
    with TestClient(fastapi_app) as client:
        response = client.post(
            '/api/v1/payments',
            headers={
                'X-API-Key': config.auth.api_key,
                'Idempotency-Key': 'idem-123',
            },
            json={
                'amount': '10.00',
                'currency': 'USD',
                'description': 'api-test',
                'metadata': {'order_id': '1'},
                'webhook_url': 'https://example.com/hook',
            },
        )
    fastapi_app.dependency_overrides.clear()

    assert response.status_code == 409
    assert 'Idempotency key "idem-123"' in response.json()['detail']


def test_get_payment_api_not_found() -> None:
    payment_id = uuid.uuid4()
    mock_service = Mock()
    mock_service.get_payment = AsyncMock(
        side_effect=PaymentNotFoundError(payment_id=payment_id),
    )
    fastapi_app.dependency_overrides[get_payments_service] = lambda: mock_service
    with TestClient(fastapi_app) as client:
        response = client.get(
            f'/api/v1/payments/{payment_id}',
            headers={'X-API-Key': config.auth.api_key},
        )
    fastapi_app.dependency_overrides.clear()

    assert response.status_code == 404
    assert f'Payment with id {payment_id} was not found.' == response.json()['detail']


def test_get_payment_api_success() -> None:
    payment_id = uuid.uuid4()
    mock_service = Mock()
    mock_service.get_payment = AsyncMock(
        return_value=PaymentDetailsResponseSchema(
            payment_id=payment_id,
            amount=Decimal('10.00'),
            currency=CurrencyEnum.USD,
            description='api-test',
            metadata={'order_id': '1'},
            status=PaymentStatusEnum.PENDING,
            idempotency_key='idem-123',
            webhook_url='https://example.com/hook',
            created_at=datetime.now(tz=UTC),
            processed_at=None,
        ),
    )
    fastapi_app.dependency_overrides[get_payments_service] = lambda: mock_service
    with TestClient(fastapi_app) as client:
        response = client.get(
            f'/api/v1/payments/{payment_id}',
            headers={'X-API-Key': config.auth.api_key},
        )
    fastapi_app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()['payment_id'] == str(payment_id)
    assert response.json()['status'] == 'pending'
    mock_service.get_payment.assert_awaited_once_with(payment_id=payment_id)
