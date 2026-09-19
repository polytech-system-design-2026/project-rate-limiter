# ABOUTME: Stage 4: every response carries X-Request-ID; an incoming one is returned unchanged.
# ABOUTME: The same id must appear in the JSON log line of the request.
import httpx

from contract_tests.helpers import require, unique_suffix


def test_request_id_generated(client: httpx.Client) -> None:
    resp = client.get("/health")
    require(
        bool(resp.headers.get("x-request-id")),
        "В ответе GET /health нет заголовка X-Request-ID. Middleware должен добавлять его "
        "к каждому ответу, генерируя uuid4, если клиент его не прислал.",
    )


def test_request_id_propagated(client: httpx.Client) -> None:
    request_id = f"test-{unique_suffix()}"
    resp = client.get("/health", headers={"X-Request-ID": request_id})
    require(
        resp.headers.get("x-request-id") == request_id,
        f"Отправили X-Request-ID: {request_id}, в ответе — {resp.headers.get('x-request-id')!r}. "
        "Пришедший идентификатор нужно вернуть тем же.",
    )
