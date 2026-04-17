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


class Configs(BaseSettings):
    """Основной класс конфигов.

    Тянет данные с .env или переменных в аргументе запуска сервиса.
    В model_config переопределены настройки базового класса:
    путь до env-файла, разделитель в синтакисе энвов, а также мягкий игнор лишних энвов.
    """

    common: CommonConfig = CommonConfig()
    db: DbConfig = DbConfig()

    model_config = SettingsConfigDict(env_file='.env', env_nested_delimiter='__', extra='allow')

    def get_db_url(self) -> str:
        """Собирает URL до БД."""
        return f'postgresql+asyncpg://{self.db.user}:{self.db.password}@{self.db.host}:{self.db.port}/{self.db.name}'


config = Configs()
