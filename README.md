# Сервис обработки платежей

Асинхронный сервис обработки платежей на FastAPI + SQLAlchemy + PostgreSQL + RabbitMQ (FastStream).

## Что умеет сервис

- `POST /api/v1/payments` — создание платежа (асинхронная обработка).
- `GET /api/v1/payments/{payment_id}` — получение текущего состояния платежа.
- Идемпотентность через заголовок `Idempotency-Key`.
- Паттерн outbox для гарантированной публикации в брокер.
- Консьюмер обработки платежей с webhook-уведомлениями.
- Повторы webhook (3 попытки, экспоненциальная задержка).
- Очередь мертвых сообщений (DLQ) после лимита доставок.

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
- `AUTH__API_KEY` — API-ключ для всех эндпоинтов.
- `DB__*` — PostgreSQL.
- `RABBIT__*` — RabbitMQ и топология очередей.
- `OUTBOX__*` — настройки диспетчера outbox.
- `WEBHOOK__*` — настройки повторов и тайм-аутов webhook-отправки.

## Запуск локально (без Docker для API и консьюмера)

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

4. Запустить API-сервис:

```bash
make dev
```

5. В отдельном терминале запустить консьюмер:

```bash
make consumer
```

## Запуск в Docker (полный стек)

```bash
make up
```

Поднимутся сервисы:
- `db` (PostgreSQL)
- `rabbitmq` (AMQP + веб-интерфейс управления)
- `migrate` (alembic upgrade head)
- `api` (FastAPI)
- `consumer` (воркер FastStream)

Остановить:

```bash
make down
```

Веб-интерфейс RabbitMQ: `http://localhost:15672`  
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

- Основной exchange: `payments.events` (тип `direct`).
- Основная очередь: `payments.new`.
- DLX: `payments.events.dlx`.
- DLQ: `payments.new.dlq`.
- Для `payments.new` используется `x-delivery-limit` (из `RABBIT__NEW_PAYMENTS_DELIVERY_LIMIT`).
- После превышения лимита повторной доставки сообщение попадает в DLQ.

## Принцип работы идемпотентности

При создании платежа заголовок `Idempotency-Key` обязателен.

- Если ключ новый, сервис создает `payment` и событие в `outbox`.
- Если ключ уже существует и payload запроса совпадает с ранее сохраненным, сервис возвращает уже существующий платеж (без дублей в БД и outbox).
- Если ключ уже существует, но payload отличается, сервис возвращает `409 Conflict`.

Таким образом повторный запрос с тем же `Idempotency-Key` безопасен и не приводит к двойному списанию/двойной постановке в обработку.

## Механизм повторной доставки

В проекте используется два уровня повторов:

- Повторы публикации outbox-событий: если отправка из `outbox` в RabbitMQ не удалась, `attempts` в таблице `outbox` увеличивается, и событие будет повторно отправляться следующими итерациями диспетчера.
- Повторная доставка сообщений консьюмеру: для очереди `payments.new` задан `x-delivery-limit`; при ошибках обработки сообщение переотправляется, а после достижения лимита направляется в `payments.new.dlq`.

Это гарантирует, что временные сбои не приводят к потере событий, а окончательно проблемные сообщения не блокируют основную очередь.

## Проверки качества

```bash
make lint
make test
```
