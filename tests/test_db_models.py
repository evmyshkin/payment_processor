from app.db.enums.currency_enum import CurrencyEnum
from app.db.enums.payment_status_enum import PaymentStatusEnum
from app.db.models.outbox_event import OutboxEvent
from app.db.models.payment import Payment


def test_currency_enum_values() -> None:
    assert CurrencyEnum.RUB.value == 'RUB'
    assert CurrencyEnum.USD.value == 'USD'
    assert CurrencyEnum.EUR.value == 'EUR'


def test_payment_status_enum_values() -> None:
    assert PaymentStatusEnum.PENDING.value == 'pending'
    assert PaymentStatusEnum.SUCCEEDED.value == 'succeeded'
    assert PaymentStatusEnum.FAILED.value == 'failed'


def test_payment_model_columns() -> None:
    columns = Payment.__table__.c

    expected = {
        'id',
        'amount',
        'currency',
        'description',
        'metadata',
        'status',
        'idempotency_key',
        'webhook_url',
        'created_at',
        'processed_at',
    }
    assert expected == set(columns.keys())
    assert columns['id'].primary_key
    assert not columns['amount'].nullable
    assert not columns['metadata'].nullable
    assert columns['idempotency_key'].unique
    assert columns['processed_at'].nullable


def test_payment_model_uses_enum_values_for_status() -> None:
    status_type = Payment.__table__.c.status.type

    assert status_type.enums == ['pending', 'succeeded', 'failed']


def test_outbox_model_columns() -> None:
    columns = OutboxEvent.__table__.c

    expected = {
        'id',
        'aggregate_id',
        'event_type',
        'payload',
        'attempts',
        'created_at',
        'published_at',
    }
    assert expected == set(columns.keys())
    assert columns['id'].primary_key
    assert not columns['payload'].nullable
    assert not columns['attempts'].nullable
    assert columns['published_at'].nullable
    assert columns['attempts'].server_default is not None
    assert str(columns['attempts'].server_default.arg) == '0'
