# ABOUTME: Stage 2: GET /health answers 200 with {"status": "ok"}.
# ABOUTME: CI and the other contract tests rely on it to know the service is ready.
import httpx
import pytest

from contract_tests.helpers import require, stopped_service


def test_health_ok(client: httpx.Client) -> None:
    resp = client.get("/health")
    require(resp.status_code == 200, f"GET /health: ожидали 200, получили {resp.status_code}.")
    require(
        resp.json() == {"status": "ok"},
        f'GET /health: ожидали тело {{"status": "ok"}}, получили {resp.text[:200]}',
    )


@pytest.mark.restarts_containers
def test_health_reports_unavailable_without_db(client: httpx.Client) -> None:
    with stopped_service(client, "db"):
        resp = client.get("/health")
    require(
        resp.status_code == 503,
        f"При остановленном PostgreSQL (docker compose stop db) GET /health вернул "
        f"{resp.status_code}, ждали 503. По этому эндпоинту CI понимает, что сервис готов: "
        "он должен ходить в базу, а не отвечать 200 всегда.",
    )
