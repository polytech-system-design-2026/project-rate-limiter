# ABOUTME: Developer commands: install, lint, tests, docker compose, contract tests, load test.
# ABOUTME: `make check` runs exactly what CI runs without Docker; README lists no-make equivalents.
.PHONY: install hooks lint format test check check-stage-1 up down test-contract loadtest

install:
	uv sync

hooks:
	uv run pre-commit install

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy app

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	@uv run pytest tests -q; code=$$?; \
	if [ $$code -eq 5 ]; then echo "Своих тестов пока нет. На этапе 1 это нормально, с этапа 2 нужно не меньше 5 (tasks/TASK-2.md)."; exit 0; fi; \
	exit $$code

check: lint test

check-stage-1:
	uv run python contract_tests/course.py test-stage-1

up:
	@test -f .env || (cp .env.example .env && echo "Создал .env из .env.example")
	docker compose up -d --build

down:
	docker compose down -v

# Требует поднятого сервиса (make up). Гоняет contract_tests/stage_2 … stage_N по полю stage.
test-contract:
	uv run python contract_tests/course.py test-contract

# Этап 3. Требует поднятого сервиса; параметры — в tasks/TASK-3.md.
loadtest:
	uv run locust -f loadtest/locustfile.py --headless --host http://localhost:8000 \
		--users 50 --spawn-rate 10 --run-time 1m
