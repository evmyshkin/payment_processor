from app.config import Configs


def test_get_db_url() -> None:
    settings = Configs(
        db={
            'user': 'postgres',
            'password': 'postgres',
            'host': 'localhost',
            'port': 5432,
            'name': 'payments',
        },
    )

    assert settings.get_db_url() == 'postgresql+asyncpg://postgres:postgres@localhost:5432/payments'


def test_get_rabbit_url() -> None:
    settings = Configs(
        rabbit={
            'user': 'guest',
            'password': 'guest',
            'host': 'rabbitmq',
            'port': 5672,
            'virtual_host': '/',
        },
    )

    assert settings.get_rabbit_url() == 'amqp://guest:guest@rabbitmq:5672/'


def test_additional_configs_defaults() -> None:
    settings = Configs()

    assert settings.auth.api_key_header_name == 'X-API-Key'
    assert settings.outbox.batch_size == 100
    assert settings.webhook.max_attempts == 3
