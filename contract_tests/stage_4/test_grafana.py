# ABOUTME: Stage 4: Grafana has the provisioned app-overview dashboard (4+ panels)
# ABOUTME: and both Prometheus and Loki data sources.
from typing import Any

import httpx

from contract_tests.helpers import eventually, read_env, require

GRAFANA_URL = "http://localhost:3000"


def grafana(path: str) -> httpx.Response | None:
    auth = ("admin", read_env("GRAFANA_ADMIN_PASSWORD", "admin"))
    try:
        return httpx.get(f"{GRAFANA_URL}{path}", auth=auth, timeout=5)
    except httpx.HTTPError:
        return None


def count_panels(panels: list[dict[str, Any]]) -> int:
    total = 0
    for panel in panels:
        if panel.get("type") == "row":
            total += count_panels(panel.get("panels", []))
        else:
            total += 1
    return total


def test_dashboard_provisioned() -> None:
    resp: httpx.Response | None = None

    def loaded() -> bool:
        nonlocal resp
        resp = grafana("/api/dashboards/uid/app-overview")
        return resp is not None and resp.status_code == 200

    require(
        eventually(loaded, timeout=30, interval=2),
        "В Grafana нет дашборда с uid app-overview "
        f"(HTTP {resp.status_code if resp is not None else 'нет ответа'}). Проверьте "
        "observability/grafana/provisioning/dashboards/dashboards.yaml и поле uid в "
        "observability/grafana/dashboards/app.json.",
    )
    assert resp is not None
    panels = count_panels(resp.json().get("dashboard", {}).get("panels", []))
    require(
        panels >= 4,
        f"На дашборде app-overview {panels} панелей, нужно не меньше 4: RPS, p95, доля 5xx "
        "и бизнес-метрика.",
    )


def test_datasources() -> None:
    resp = grafana("/api/datasources")
    require(
        resp is not None and resp.status_code == 200,
        "Не удалось получить список источников данных Grafana. Логин admin, пароль — "
        "GRAFANA_ADMIN_PASSWORD из .env.",
    )
    assert resp is not None
    types = {ds.get("type") for ds in resp.json()}
    missing = sorted({"prometheus", "loki"} - types)
    require(
        not missing,
        f"В Grafana нет источников данных: {', '.join(missing)}. Проверьте "
        "observability/grafana/provisioning/datasources/datasources.yaml.",
    )
