# ABOUTME: Stage 4: a request's JSON log line reaches Loki through Alloy and is found by request_id.
# ABOUTME: Checks the required log fields of that line.
import json
import time
from typing import Any

import httpx

from contract_tests.helpers import eventually, require, unique_suffix

LOKI_URL = "http://localhost:3100"
REQUIRED_FIELDS = {
    "timestamp",
    "level",
    "message",
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
}


def find_lines(request_id: str, since_ns: int) -> list[str]:
    try:
        resp = httpx.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": f'{{service="app"}} |= "{request_id}"',
                "start": str(since_ns),
                "limit": "20",
            },
            timeout=5,
        )
    except httpx.HTTPError:
        return []
    if resp.status_code != 200:
        return []
    lines: list[str] = []
    for stream in resp.json().get("data", {}).get("result", []):
        lines.extend(value[1] for value in stream.get("values", []))
    return lines


def parse(line: str) -> dict[str, Any] | None:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return None
    return record if isinstance(record, dict) else None


def test_request_log_in_loki(client: httpx.Client) -> None:
    since_ns = (time.time_ns()) - 60 * 10**9
    request_id = f"loki-{unique_suffix()}"
    client.get("/health", headers={"X-Request-ID": request_id})

    lines: list[str] = []

    def found() -> bool:
        nonlocal lines
        lines = find_lines(request_id, since_ns)
        return bool(lines)

    require(
        eventually(found, timeout=60, interval=2),
        f"За 60 с в Loki не нашлось ни одной строки с request_id {request_id} "
        '(запрос {service="app"} |= "<id>"). Проверьте по порядку: приложение пишет '
        "request_id в лог (docker compose logs app), Alloy видит контейнеры "
        "(http://localhost:12345), Loki готов (http://localhost:3100/ready).",
    )
    records = [r for r in map(parse, lines) if r is not None]
    require(
        records,
        f"Строка лога с request_id {request_id} — не JSON: {lines[0][:300]}",
    )
    # Строк с этим request_id может быть несколько (бизнес-события пишутся с ним же),
    # поэтому ищем строку запроса — ту, где есть все обязательные поля.
    complete = [r for r in records if not REQUIRED_FIELDS - r.keys()]
    if not complete:
        closest = min(records, key=lambda r: len(REQUIRED_FIELDS - r.keys()))
        missing = sorted(REQUIRED_FIELDS - closest.keys())
        require(
            False,
            f"Ни в одной строке лога запроса нет всех обязательных полей. Не хватает: "
            f"{', '.join(missing)}. Строка: {json.dumps(closest, ensure_ascii=False)[:300]}",
        )
