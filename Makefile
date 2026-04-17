# Локальная разработка
dev:
	uv run uvicorn app.main:fastapi_app --host 127.0.0.1 --port "8000" --reload
consumer:
	uv run faststream run app.consumer.main:app
migrate:
	uv run alembic upgrade head
migrate-down:
	uv run alembic downgrade -1

# Docker разработка
db:
	docker compose up --build db -d
broker:
	docker compose up --build rabbitmq -d
up:
	docker compose up --build -d
up-stack:
	docker compose up --build -d
down:
	docker compose down

# Запустить пре-коммит линтер и форматтер
lint:
	uv run pre-commit run --all-files

test:
	uv run pytest

test-cov:
	uv run pytest --cov=app --cov-branch --cov-report=term-missing
