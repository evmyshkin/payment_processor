from pydantic import BaseModel
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

from app.utils.enums.log_level_enum import LogLevelEnum


class CommonConfig(BaseModel):
    app_name: str = 'payment_processor'
    prometheus_enabled: bool = True
    log_level: LogLevelEnum = LogLevelEnum.INFO
    request_body_log_max_chars: int = 2048
    disabled_log_endpoints: list[str] = [
        '/healthcheck',
        '/metrics',
        '/openapi.json',
        '/docs',
    ]


class DbConfig(BaseModel):
    user: str = ''
    password: str = ''
    host: str = ''
    port: int = 5432
    name: str = ''


class AuthConfig(BaseModel):
    api_key_header_name: str = 'X-API-Key'
    api_key: str = ''


class RabbitConfig(BaseModel):
    user: str = 'guest'
    password: str = 'guest'
    host: str = 'localhost'
    port: int = 5672
    virtual_host: str = '/'
    exchange_name: str = 'payments.events'
    new_payments_queue_name: str = 'payments.new'
    dead_letter_exchange_name: str = 'payments.events.dlx'
    dead_letter_queue_name: str = 'payments.new.dlq'
    new_payments_routing_key: str = 'payments.new'
    dead_letter_routing_key: str = 'payments.new.dlq'


class OutboxConfig(BaseModel):
    batch_size: int = 100
    poll_interval_seconds: float = 1.0


class WebhookConfig(BaseModel):
    timeout_seconds: float = 5.0
    max_attempts: int = 3
    retry_backoff_base_seconds: float = 1.0


class Configs(BaseSettings):
    """Основной класс конфигов.

    Тянет данные с .env или переменных в аргументе запуска сервиса.
    В model_config переопределены настройки базового класса:
    путь до env-файла, разделитель в синтакисе энвов, а также мягкий игнор лишних энвов.
    """

    common: CommonConfig = CommonConfig()
    db: DbConfig = DbConfig()
    auth: AuthConfig = AuthConfig()
    rabbit: RabbitConfig = RabbitConfig()
    outbox: OutboxConfig = OutboxConfig()
    webhook: WebhookConfig = WebhookConfig()

    model_config = SettingsConfigDict(env_file='.env', env_nested_delimiter='__', extra='allow')

    def get_db_url(self) -> str:
        """Собирает URL до БД."""
        return f'postgresql+asyncpg://{self.db.user}:{self.db.password}@{self.db.host}:{self.db.port}/{self.db.name}'

    def get_rabbit_url(self) -> str:
        """Собирает URL до RabbitMQ."""
        virtual_host = self.rabbit.virtual_host.lstrip('/')
        return f'amqp://{self.rabbit.user}:{self.rabbit.password}@{self.rabbit.host}:{self.rabbit.port}/{virtual_host}'


config = Configs()
