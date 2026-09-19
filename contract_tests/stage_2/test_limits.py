# ABOUTME: Stage 2 contract of the rate limiter: rules API, per-IP and global limits, 429 format,
# ABOUTME: client IP from X-Forwarded-For, rules persistence. Tests use a 3-second window.
import time
from typing import Any

import httpx
import pytest

from contract_tests.helpers import compose, require, wait_until_healthy
from contract_tests.limiter import (
    HIGH,
    WINDOW,
    hit,
    set_limits,
    statuses,
    unique_ip,
    with_retries,
)


def test_resource_ok(client: httpx.Client) -> None:
    set_limits(client, HIGH, HIGH)
    resp = hit(client, unique_ip())
    require(
        resp.status_code == 200 and resp.json() == {"message": "ok"},
        f'GET /resource: ждали 200 {{"message": "ok"}}, получили {resp.status_code} '
        f"{resp.text[:200]}",
    )


def test_get_limits_returns_put_values(client: httpx.Client) -> None:
    put = set_limits(client, 1234, 56, window=7)
    want = {
        "global": {"limit": 1234, "window_seconds": 7},
        "per_ip": {"limit": 56, "window_seconds": 7},
    }
    require(put == want, f"PUT /limits должен вернуть сохранённые правила {want}, вернул {put}.")
    got = client.get("/limits")
    require(
        got.status_code == 200 and got.json() == want,
        f"GET /limits после PUT: ждали {want}, получили {got.status_code} {got.text[:300]}",
    )


@pytest.mark.parametrize(
    "body",
    [
        {"global": {"limit": 0, "window_seconds": 3}, "per_ip": {"limit": 1, "window_seconds": 3}},
        {"global": {"limit": 1, "window_seconds": 3}, "per_ip": {"limit": 1, "window_seconds": 0}},
        {"global": {"limit": -5, "window_seconds": 3}, "per_ip": {"limit": 1, "window_seconds": 3}},
        {"global": {"limit": 1, "window_seconds": 3}},
        {},
    ],
)
def test_put_limits_rejects_invalid(client: httpx.Client, body: dict[str, Any]) -> None:
    resp = client.put("/limits", json=body)
    require(
        resp.status_code == 422,
        f"PUT /limits с телом {body}: ожидали 422, получили {resp.status_code}.",
    )


def test_per_ip_limit(client: httpx.Client) -> None:
    limit = 5
    set_limits(client, HIGH, limit)

    def scenario() -> str | None:
        ip = unique_ip()
        codes = statuses([hit(client, ip) for _ in range(limit + 1)])
        if codes != [200] * limit + [429]:
            return (
                f"per_ip.limit = {limit}, окно {WINDOW} с: {limit + 1} быстрых запросов с одного "
                f"адреса должны дать {limit} × 200 и затем 429, получили {codes}."
            )
        return None

    with_retries(scenario)


def test_429_format(client: httpx.Client) -> None:
    set_limits(client, HIGH, 1)

    def scenario() -> str | None:
        ip = unique_ip()
        hit(client, ip)
        resp = hit(client, ip)
        if resp.status_code != 429:
            return (
                f"per_ip.limit = 1: второй запрос должен получить 429, получил {resp.status_code}."
            )
        body = resp.json()
        header = resp.headers.get("retry-after", "")
        retry_after = body.get("retry_after")
        if body.get("detail") != "rate limit exceeded" or not isinstance(retry_after, int):
            return (
                'Тело 429 должно быть {"detail": "rate limit exceeded", "retry_after": <целое>}, '
                f"получили {body}."
            )
        if header != str(retry_after):
            return (
                f"Заголовок Retry-After ({header!r}) должен совпадать с retry_after в теле "
                f"({retry_after})."
            )
        if not 1 <= retry_after <= WINDOW:
            return f"retry_after = {retry_after}, а должно быть от 1 до {WINDOW} (окно {WINDOW} с)."
        return None

    with_retries(scenario)


def test_limit_resets_after_window(client: httpx.Client) -> None:
    limit = 3
    set_limits(client, HIGH, limit)
    ip = unique_ip()
    for _ in range(limit + 1):
        hit(client, ip)
    time.sleep(WINDOW + 1)
    resp = hit(client, ip)
    require(
        resp.status_code == 200,
        f"Через {WINDOW + 1} с после исчерпания лимита (окно {WINDOW} с) запрос должен пройти, "
        f"получили {resp.status_code}.",
    )


def test_other_ip_not_affected(client: httpx.Client) -> None:
    set_limits(client, HIGH, 2)
    a, b = unique_ip(), unique_ip()

    def scenario() -> str | None:
        codes_a = statuses([hit(client, a) for _ in range(3)])
        if codes_a[-1] != 429:
            return (
                f"Адрес A исчерпал per_ip.limit = 2, третий запрос должен получить 429: {codes_a}."
            )
        resp_b = hit(client, b)
        if resp_b.status_code != 200:
            return f"Адрес B не должен страдать от лимита A: получил {resp_b.status_code}."
        return None

    with_retries(scenario)


def test_first_forwarded_address_is_client(client: httpx.Client) -> None:
    set_limits(client, HIGH, 1)

    def scenario() -> str | None:
        ip = unique_ip()
        first = client.get("/resource", headers={"X-Forwarded-For": ip})
        second = client.get("/resource", headers={"X-Forwarded-For": f"{ip}, 10.1.2.3"})
        if first.status_code != 200 or second.status_code != 429:
            return (
                "IP клиента — первый адрес из X-Forwarded-For: запросы с «A» и «A, 10.1.2.3» — "
                f"один клиент. При per_ip.limit = 1 ждали 200 и 429, получили "
                f"{first.status_code} и {second.status_code}."
            )
        return None

    with_retries(scenario)


def test_global_limit(client: httpx.Client) -> None:
    set_limits(client, 5, HIGH)

    def scenario() -> str | None:
        # Пауза на окно: запросы предыдущих тестов не должны учитываться в глобальном счётчике.
        time.sleep(WINDOW + 1)
        a, b, c = unique_ip(), unique_ip(), unique_ip()
        codes = statuses([hit(client, ip) for ip in (a, a, a, b, b, c)])
        if codes != [200] * 5 + [429]:
            return (
                "global.limit = 5, per_ip.limit большой: 3 запроса от A и 2 от B проходят, "
                f"6-й от C должен получить 429. Получили {codes}."
            )
        return None

    try:
        with_retries(scenario)
    finally:
        set_limits(client, HIGH, HIGH)


def test_rules_applied_without_restart(client: httpx.Client) -> None:
    set_limits(client, HIGH, HIGH)

    def scenario() -> str | None:
        ip = unique_ip()
        before = hit(client, ip).status_code
        set_limits(client, HIGH, 1)
        codes = statuses([hit(client, ip), hit(client, ip)])
        set_limits(client, HIGH, HIGH)
        if before != 200 or codes[-1] != 429:
            return (
                "После PUT /limits с per_ip.limit = 1 новые правила должны действовать сразу: "
                f"ждали, что второй запрос получит 429, получили {codes}."
            )
        return None

    with_retries(scenario)


@pytest.mark.restarts_containers
def test_rules_survive_app_restart(client: httpx.Client) -> None:
    want = set_limits(client, 4321, 87, window=9)
    compose("restart", "app")
    wait_until_healthy(client)
    got = client.get("/limits")
    require(
        got.status_code == 200 and got.json() == want,
        f"После docker compose restart app GET /limits вернул {got.text[:300]} вместо {want}. "
        "Правила должны храниться в PostgreSQL, а не в памяти процесса.",
    )
    set_limits(client, HIGH, HIGH)
