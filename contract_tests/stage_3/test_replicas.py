# ABOUTME: Stage 3 contract of the rate limiter: two app instances behind nginx share counters
# ABOUTME: in Redis, and rules keep working from the cache while PostgreSQL is stopped.
import httpx
import pytest

from contract_tests.helpers import compose, require, stopped_service, wait_until_healthy
from contract_tests.limiter import HIGH, hit, set_limits, statuses, unique_ip, with_retries


def test_counters_shared_between_instances(client: httpx.Client) -> None:
    limit = 10
    set_limits(client, HIGH, limit)
    instances: set[str] = set()

    def scenario() -> str | None:
        ip = unique_ip()
        responses = [hit(client, ip) for _ in range(limit + 1)]
        missing = [r for r in responses if not r.headers.get("x-instance")]
        if missing:
            return "В ответах нет заголовка X-Instance с именем экземпляра (hostname контейнера)."
        instances.update(r.headers["x-instance"] for r in responses)
        codes = statuses(responses)
        if codes != [200] * limit + [429]:
            return (
                f"per_ip.limit = {limit} через nginx на порту 8000: ждали ровно {limit} × 200 и "
                f"затем 429, получили {codes}. Если прошло больше — счётчики у экземпляров свои, "
                "а должны быть общими, в Redis."
            )
        return None

    with_retries(scenario)
    require(
        len(instances) >= 2,
        f"Все ответы пришли от одного экземпляра ({instances}). Нужны два экземпляра app "
        "(deploy.replicas: 2) за nginx, который распределяет запросы между ними.",
    )


@pytest.mark.restarts_containers
def test_limits_without_database(client: httpx.Client) -> None:
    set_limits(client, HIGH, 2)
    # Перезапуск app стирает кэш правил внутри процесса: пройти тест можно только с Redis.
    compose("restart", "app")
    wait_until_healthy(client)
    with stopped_service(client, "db"):

        def scenario() -> str | None:
            ip = unique_ip()
            codes = statuses([hit(client, ip) for _ in range(3)])
            if codes != [200, 200, 429]:
                return (
                    "При остановленном PostgreSQL (docker compose stop db) /resource должен "
                    f"применять действующие правила: при per_ip.limit = 2 ждали [200, 200, 429], "
                    f"получили {codes}. Правила нужно кэшировать в Redis."
                )
            return None

        with_retries(scenario)
    set_limits(client, HIGH, HIGH)
