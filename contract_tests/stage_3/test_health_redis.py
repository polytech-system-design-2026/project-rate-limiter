# ABOUTME: Stage 3: /health answers 503 while Redis is stopped, proving Redis is really used.
# ABOUTME: Do not edit — CI replaces contract_tests/ with the template copy at tag reference-v1.
import httpx
import pytest

from contract_tests.helpers import require, stopped_service


@pytest.mark.restarts_containers
def test_health_reports_unavailable_without_redis(client: httpx.Client) -> None:
    with stopped_service(client, "redis"):
        resp = client.get("/health")
    require(
        resp.status_code == 503,
        f"При остановленном Redis (docker compose stop redis) GET /health вернул "
        f"{resp.status_code}, ждали 503. С этапа 3 проверка готовности включает и Redis.",
    )
