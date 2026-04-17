# Payment Processor

Асинхронный сервис обработки платежей на FastAPI + SQLAlchemy + PostgreSQL + RabbitMQ (FastStream).

## Что умеет сервис

- `POST /api/v1/payments` — создание платежа (асинхронная обработка).
- `GET /api/v1/payments/{payment_id}` — получение текущего состояния платежа.
- Idempotency через заголовок `Idempotency-Key`.
- Outbox pattern для гарантированной публикации в брокер.
- Consumer обработки платежей с webhook-уведомлениями.
- Retry webhook (3 попытки, экспоненциальная задержка).
- DLQ для сообщений после лимита доставок.

## Требования

- Python `3.14.2+`
- `uv`
- Docker + Docker Compose

## Конфигурация

1. Скопировать пример:

```bash
cp .env-example .env
```

2. При необходимости поменять значения в `.env`.

Ключевые параметры:
- `AUTH__API_KEY` — API key для всех endpoint.
- `DB__*` — PostgreSQL.
- `RABBIT__*` — RabbitMQ и топология очередей.
- `OUTBOX__*` — настройки outbox dispatcher.
- `WEBHOOK__*` — retry/timeout webhook отправки.

## Запуск локально (без Docker для API/consumer)

1. Установить зависимости:

```bash
uv sync
```

2. Поднять инфраструктуру БД:

```bash
make db
```

3. Применить миграции:

```bash
make migrate
```

4. Запустить API:

```bash
make dev
```

5. В отдельном терминале запустить consumer:

```bash
make consumer
```

## Запуск в Docker (полный стек)

```bash
make up
```

Поднимутся сервисы:
- `db` (PostgreSQL)
- `rabbitmq` (AMQP + management UI)
- `migrate` (alembic upgrade head)
- `api` (FastAPI)
- `consumer` (FastStream worker)

Остановить:

```bash
make down
```

RabbitMQ management UI: `http://localhost:15672`  
По умолчанию: `guest/guest`.

## Примеры запросов

### Создание платежа

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/payments' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: local-api-key' \
  -H 'Idempotency-Key: payment-1' \
  -d '{
    "amount": "100.00",
    "currency": "RUB",
    "description": "Оплата заказа #1",
    "metadata": {
      "order_id": "1"
    },
    "webhook_url": "https://example.com/webhook"
  }'
```

### Получение платежа

```bash
curl -X GET 'http://127.0.0.1:8000/api/v1/payments/<payment_id>' \
  -H 'accept: application/json' \
  -H 'X-API-Key: local-api-key'
```

## Очереди и доставка

- Основной exchange: `payments.events` (direct).
- Основная очередь: `payments.new`.
- DLX: `payments.events.dlx`.
- DLQ: `payments.new.dlq`.
- Для `payments.new` используется `x-delivery-limit` (из `RABBIT__NEW_PAYMENTS_DELIVERY_LIMIT`).
- После превышения лимита redelivery сообщение попадает в DLQ.

## Проверки качества

```bash
make lint
make test
```
