# ABOUTME: Stage 2+: operations designed in docs/openapi.yaml match the live GET /openapi.json.
# ABOUTME: Compares method + path only; service endpoints like /health and /metrics are ignored.
import httpx

from contract_tests.helpers import load_openapi_yaml, normalize_path, require, spec_operations

IGNORED_PATHS = {normalize_path(p) for p in ("/health", "/metrics", "/docs", "/openapi.json")}


def describe(ops: set[tuple[str, str]]) -> str:
    return ", ".join(f"{m.upper()} {p}" for m, p in sorted(ops, key=lambda o: (o[1], o[0])))


def test_designed_operations_match_implementation(client: httpx.Client) -> None:
    resp = client.get("/openapi.json")
    require(
        resp.status_code == 200,
        f"GET /openapi.json: ожидали 200, получили {resp.status_code}. "
        "Не отключайте openapi_url у FastAPI.",
    )
    designed = {op for op in spec_operations(load_openapi_yaml()) if op[1] not in IGNORED_PATHS}
    live = {op for op in spec_operations(resp.json()) if op[1] not in IGNORED_PATHS}
    only_designed = designed - live
    only_live = live - designed
    problems = []
    if only_designed:
        problems.append(
            f"описаны в docs/openapi.yaml, но не реализованы: {describe(only_designed)}"
        )
    if only_live:
        problems.append(f"реализованы, но не описаны в docs/openapi.yaml: {describe(only_live)}")
    require(
        not problems,
        "Спецификация и реализация разошлись ({} — параметр пути):\n  "
        + "\n  ".join(problems)
        + "\nОбновите docs/openapi.yaml или код, чтобы они совпадали.",
    )
