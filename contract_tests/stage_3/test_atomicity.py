# ABOUTME: Stage 3: counters are shared and updated atomically — parallel bursts must not let
# ABOUTME: more requests through than the limit, for the per-IP rule and for the global rule.
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

from contract_tests.helpers import require
from contract_tests.limiter import HIGH, WINDOW, hit, set_limits, unique_ip


def burst(client: httpx.Client, addresses: list[str]) -> list[int]:
    """Шлёт запросы одновременно: проверка и увеличение счётчика должны быть атомарны."""
    with ThreadPoolExecutor(max_workers=len(addresses)) as pool:
        responses = list(pool.map(lambda ip: hit(client, ip), addresses))
    return [r.status_code for r in responses]


def test_per_ip_limit_under_parallel_load(client: httpx.Client) -> None:
    limit = 10
    set_limits(client, HIGH, limit)
    ip = unique_ip()
    codes = burst(client, [ip] * (limit * 2))
    passed = codes.count(200)
    require(
        passed == limit,
        f"per_ip.limit = {limit}, окно {WINDOW} с: {limit * 2} одновременных запросов с одного "
        f"адреса — прошло {passed}, ждали ровно {limit}. Проверка и увеличение счётчика должны "
        "быть атомарны (Lua-скрипт, MULTI/EXEC или INCR), а не «прочитал, сравнил, записал».",
    )


def test_global_limit_under_parallel_load(client: httpx.Client) -> None:
    limit = 10
    set_limits(client, limit, HIGH)
    # Ждём окно: запросы предыдущих тестов не должны попадать в глобальный счётчик.
    time.sleep(WINDOW + 1)
    addresses = [unique_ip() for _ in range(limit * 2)]
    codes = burst(client, addresses)
    passed = codes.count(200)
    set_limits(client, HIGH, HIGH)
    require(
        passed == limit,
        f"global.limit = {limit}: {limit * 2} одновременных запросов с разных адресов — прошло "
        f"{passed}, ждали ровно {limit}. Глобальный счётчик тоже общий для экземпляров и "
        "обновляется атомарно.",
    )
