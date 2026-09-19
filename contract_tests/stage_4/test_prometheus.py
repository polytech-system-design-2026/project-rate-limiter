# ABOUTME: Stage 4: Prometheus scrapes the app (target up) and has AppDown and HighErrorRate loaded.
# ABOUTME: Talks to Prometheus HTTP API on localhost:9090.
from typing import Any

import httpx

from contract_tests.helpers import eventually, require

PROMETHEUS_URL = "http://localhost:9090"
REQUIRED_ALERTS = {"AppDown", "HighErrorRate"}


def api(path: str) -> dict[str, Any]:
    try:
        resp = httpx.get(f"{PROMETHEUS_URL}{path}", timeout=5)
    except httpx.HTTPError:
        return {}
    return resp.json().get("data", {}) if resp.status_code == 200 else {}


def app_targets() -> list[dict[str, Any]]:
    targets = api("/api/v1/targets").get("activeTargets", [])
    return [t for t in targets if t.get("labels", {}).get("job") == "app"]


def test_app_target_up(client: httpx.Client) -> None:
    require(
        eventually(lambda: bool(app_targets()), timeout=30, interval=2),
        'В Prometheus нет target с job="app". Проверьте observability/prometheus/prometheus.yml: '
        "job_name: app и адрес app:8000.",
    )
    require(
        eventually(
            lambda: all(t.get("health") == "up" for t in app_targets()), timeout=30, interval=2
        ),
        "Target app в Prometheus не в состоянии up: "
        + "; ".join(f"{t.get('scrapeUrl')}: {t.get('lastError')}" for t in app_targets())
        + ". Проверьте, что GET /metrics отдаёт метрики в формате Prometheus.",
    )


def test_alert_rules_loaded() -> None:
    groups = api("/api/v1/rules").get("groups", [])
    names = {rule.get("name") for group in groups for rule in group.get("rules", [])}
    missing = sorted(REQUIRED_ALERTS - names)
    require(
        not missing,
        f"В Prometheus не загружены правила: {', '.join(missing)}. Проверьте rule_files в "
        "prometheus.yml и observability/prometheus/rules.yml (имена правил — как в задании).",
    )
