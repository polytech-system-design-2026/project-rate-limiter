# ABOUTME: Helpers for rate limiter contract tests: setting rules, unique client IPs, bursts.
# ABOUTME: A burst check is retried because a fixed-window boundary may fall inside a burst.
import random
import time
from collections.abc import Callable

import httpx

from contract_tests.helpers import require

WINDOW = 3
HIGH = 100_000
ATTEMPTS = 3


def unique_ip() -> str:
    """Адрес из диапазона документации 198.18.0.0/15: у каждого теста свой."""
    return f"198.{random.randint(18, 19)}.{random.randint(0, 255)}.{random.randint(1, 254)}"


def set_limits(
    client: httpx.Client, global_limit: int, per_ip_limit: int, window: int = WINDOW
) -> dict[str, dict[str, int]]:
    body = {
        "global": {"limit": global_limit, "window_seconds": window},
        "per_ip": {"limit": per_ip_limit, "window_seconds": window},
    }
    resp = client.put("/limits", json=body)
    require(
        resp.status_code == 200,
        f"PUT /limits {body}: ожидали 200, получили {resp.status_code}: {resp.text[:300]}",
    )
    result: dict[str, dict[str, int]] = resp.json()
    return result


def hit(client: httpx.Client, ip: str) -> httpx.Response:
    return client.get("/resource", headers={"X-Forwarded-For": ip})


def statuses(responses: list[httpx.Response]) -> list[int]:
    return [r.status_code for r in responses]


def with_retries(scenario: Callable[[], str | None]) -> None:
    """Повторяет сценарий, пока он не пройдёт, но не больше ATTEMPTS раз.

    Сценарий возвращает None при успехе или текст ошибки. Повтор нужен, потому что
    в алгоритме fixed window граница окна может случайно попасть внутрь серии
    запросов, и тогда лимит «обнуляется» на середине. Неверная реализация падает
    на каждой попытке.
    """
    error = None
    for attempt in range(ATTEMPTS):
        if attempt:
            time.sleep(WINDOW + 1)
        error = scenario()
        if error is None:
            return
    require(False, f"{error}\n(Сценарий повторён {ATTEMPTS} раза с паузой {WINDOW + 1} с.)")
