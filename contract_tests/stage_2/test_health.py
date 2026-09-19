# ABOUTME: Stage 2: GET /health answers 200 with {"status": "ok"}.
# ABOUTME: CI and the other contract tests rely on it to know the service is ready.
import httpx

from contract_tests.helpers import require


def test_health_ok(client: httpx.Client) -> None:
    resp = client.get("/health")
    require(resp.status_code == 200, f"GET /health: ожидали 200, получили {resp.status_code}.")
    require(
        resp.json() == {"status": "ok"},
        f'GET /health: ожидали тело {{"status": "ok"}}, получили {resp.text[:200]}',
    )
