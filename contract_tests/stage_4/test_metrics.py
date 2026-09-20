# ABOUTME: Stage 4 metrics of the rate limiter, read through Prometheus because two app replicas
# ABOUTME: each expose only their own /metrics: HTTP counters, histogram, ratelimit_rejected_total.
from typing import Any

import httpx

from contract_tests.helpers import eventually, require, unique_suffix
from contract_tests.limiter import HIGH, hit, set_limits, unique_ip

PROMETHEUS_URL = "http://localhost:9090"
SCRAPE_WAIT = 30.0


def query(expr: str) -> list[dict[str, Any]]:
    try:
        resp = httpx.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": expr}, timeout=5)
    except httpx.HTTPError:
        return []
    if resp.status_code != 200:
        return []
    result: list[dict[str, Any]] = resp.json().get("data", {}).get("result", [])
    return result


def value(expr: str) -> float:
    result = query(expr)
    return float(result[0]["value"][1]) if result else 0.0


def test_metrics_endpoint(client: httpx.Client) -> None:
    resp = client.get("/metrics")
    require(
        resp.status_code == 200 and "http_requests_total" in resp.text,
        f"GET /metrics: ждали 200 и метрику http_requests_total, получили {resp.status_code}.",
    )


def test_http_requests_total_counts_requests(client: httpx.Client) -> None:
    expr = 'sum(http_requests_total{job="app", method="GET", path="/limits"})'
    before = value(expr)
    for _ in range(5):
        client.get("/limits")
    require(
        eventually(lambda: value(expr) - before >= 5, SCRAPE_WAIT, interval=2),
        f'После 5 запросов GET /limits сумма http_requests_total{{path="/limits"}} по обоим '
        f"экземплярам в Prometheus выросла на {value(expr) - before:g}, ждали не меньше 5.",
    )


def test_unknown_paths_do_not_create_series(client: httpx.Client) -> None:
    require(
        bool(query('up{job="app"}')),
        'Prometheus не отдаёт метрики сервиса (up{job="app"} пуст) — проверить метки не на чем.',
    )
    raw = f"/no/such/page-{unique_suffix()}"
    before_404 = value('sum(http_requests_total{job="app", status="404"})')
    client.get(raw)
    require(
        eventually(
            lambda: value('sum(http_requests_total{job="app", status="404"})') - before_404 >= 1,
            SCRAPE_WAIT,
            interval=2,
        ),
        'Ответ 404 не попал в http_requests_total с меткой status="404". Считайте метрики для '
        "любого ответа, включая ошибки, — иначе доля 5xx и алерт HighErrorRate не работают.",
    )
    found = query(f'http_requests_total{{path="{raw}"}}')
    require(
        not found,
        f"Запрос на несуществующий путь {raw} создал в http_requests_total метку path с сырым "
        "путём. В path — только шаблон маршрута; для запросов мимо маршрутов — одно общее "
        "значение, иначе любой сканер создаст тысячи временных рядов.",
    )


def test_request_duration_histogram(client: httpx.Client) -> None:
    client.get("/health")
    require(
        eventually(
            lambda: value('count(http_request_duration_seconds_bucket{job="app"})') > 0,
            SCRAPE_WAIT,
            interval=2,
        ),
        "В Prometheus нет гистограммы http_request_duration_seconds (сэмплов *_bucket). "
        "Используйте Histogram из prometheus-client с метками method и path.",
    )


def test_ratelimit_rejected_total_grows(client: httpx.Client) -> None:
    expr = 'sum(ratelimit_rejected_total{job="app"})'
    before = value(expr)
    set_limits(client, HIGH, 1)
    ip = unique_ip()
    codes = [hit(client, ip).status_code for _ in range(3)]
    set_limits(client, HIGH, HIGH)
    require(429 in codes, f"per_ip.limit = 1: из трёх запросов ни один не получил 429 ({codes}).")
    rejected = codes.count(429)
    require(
        eventually(lambda: value(expr) - before >= rejected, SCRAPE_WAIT, interval=2),
        f"После {rejected} ответов 429 сумма ratelimit_rejected_total в Prometheus выросла на "
        f"{value(expr) - before:g}. Метрика — counter, увеличивается на каждый ответ 429.",
    )
