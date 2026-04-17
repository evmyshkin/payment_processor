# Локальная разработка
dev:
	uvicorn app.main:fastapi_app --host 127.0.0.1 --port "3000" --reload
migrate:
	alembic upgrade head
migrate-down:
	alembic downgrade -1

# Docker разработка
db:
	docker compose up --build db -d
up:
	docker compose up -d
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
