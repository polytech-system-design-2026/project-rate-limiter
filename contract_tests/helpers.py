# ABOUTME: Shared helpers for contract tests: messages, path normalization, docker compose control.
# ABOUTME: Do not edit — CI replaces contract_tests/ with the template copy at tag reference-v1.
import re
import subprocess
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from prometheus_client.parser import text_string_to_metric_families

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def require(condition: object, message: str) -> None:
    """Проверка с сообщением для студента, без трейсбека тестового кода."""
    if not condition:
        pytest.fail(message, pytrace=False)


def normalize_path(path: str) -> str:
    """Имена параметров не важны: /links/{code} и /links/{short_code} — одна операция."""
    return re.sub(r"\{[^}]*\}", "{}", path.rstrip("/") or "/")


def spec_operations(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    """Операции OpenAPI-спецификации: (метод, нормализованный путь) -> объект операции."""
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for path, item in (spec.get("paths") or {}).items():
        for method, op in (item or {}).items():
            if method in HTTP_METHODS and isinstance(op, dict):
                result[(method, normalize_path(path))] = op
    return result


def unique_suffix() -> str:
    return uuid.uuid4().hex[:12]


def eventually(check: Callable[[], bool], timeout: float, interval: float = 0.5) -> bool:
    """Повторяет check, пока он не вернёт True или не выйдет время."""
    deadline = time.monotonic() + timeout
    while True:
        if check():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(interval)


def wait_until_healthy(client: httpx.Client, timeout: float = 60.0) -> None:
    """Ждёт 200 от GET /health, иначе падает с подсказкой, куда смотреть."""
    last = "нет ответа"

    def healthy() -> bool:
        nonlocal last
        try:
            resp = client.get("/health")
        except httpx.HTTPError as exc:
            last = f"{type(exc).__name__}: {exc}"
            return False
        last = f"HTTP {resp.status_code}: {resp.text[:200]}"
        return resp.status_code == 200

    require(
        eventually(healthy, timeout, interval=2),
        f"Сервис на {client.base_url} не ответил 200 на GET /health за {timeout:.0f} с "
        f"(последний ответ: {last}). Поднимите сервис (make up) и посмотрите "
        "docker compose logs app.",
    )


def compose(*args: str, timeout: float = 120) -> None:
    """Команда docker compose в корне репозитория; ошибка — понятным сообщением."""
    cmd = ["docker", "compose", *args]
    try:
        result = subprocess.run(
            cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        pytest.fail("Не найдена команда docker. Установите Docker Desktop.", pytrace=False)
    require(
        result.returncode == 0,
        f"Команда «{' '.join(cmd)}» завершилась с ошибкой:\n{result.stderr[-1000:]}",
    )


@contextmanager
def stopped_service(client: httpx.Client, service: str) -> Iterator[None]:
    """Останавливает сервис compose на время блока и возвращает всё как было."""
    compose("stop", service)
    try:
        yield
    finally:
        compose("start", service)
        wait_until_healthy(client)


def read_env(name: str, default: str) -> str:
    """Значение переменной из .env в корне репозитория (его создаёт make up или CI)."""
    env = PROJECT_ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == name:
                return value.strip().strip("\"'")
    return default


OPENAPI_YAML = PROJECT_ROOT / "docs" / "openapi.yaml"


def load_openapi_yaml() -> dict[str, Any]:
    if not OPENAPI_YAML.exists():
        pytest.fail(
            "Не найден docs/openapi.yaml. Верните файл из шаблона и опишите в нём API "
            "(tasks/TASK-1.md).",
            pytrace=False,
        )
    raw = OPENAPI_YAML.read_text(encoding="utf-8")
    if "\t" in raw:
        line = next(n for n, s in enumerate(raw.splitlines(), start=1) if "\t" in s)
        pytest.fail(
            f"В docs/openapi.yaml табуляция (первая — строка {line}). YAML допускает только "
            "пробелы: включите в редакторе «отступ пробелами» и замените табы.",
            pytrace=False,
        )
    # pytest.fail вызывается вне except, чтобы в выводе не было исходного исключения.
    error = ""
    try:
        spec = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        error = str(exc)
    require(not error, f"docs/openapi.yaml не читается как YAML: {error}")
    if not isinstance(spec, dict):
        pytest.fail(
            "docs/openapi.yaml пустой или не является YAML-объектом. Начните с полей "
            "openapi, info и paths (пример — в самом файле шаблона).",
            pytrace=False,
        )
    return spec


def metric_samples(client: httpx.Client) -> list[tuple[str, dict[str, str], float]]:
    """Все сэмплы из GET /metrics: (имя, метки, значение)."""
    resp = client.get("/metrics")
    require(
        resp.status_code == 200,
        f"GET /metrics: ожидали 200, получили {resp.status_code}. Эндпоинт метрик — этап 4.",
    )
    error = ""
    samples: list[tuple[str, dict[str, str], float]] = []
    try:
        for family in text_string_to_metric_families(resp.text):
            samples.extend((s.name, dict(s.labels), s.value) for s in family.samples)
    except ValueError as exc:
        error = str(exc)
    require(not error, f"GET /metrics отдаёт не формат Prometheus: {error}")
    return samples


def metric_sum(samples: list[tuple[str, dict[str, str], float]], name: str, **labels: str) -> float:
    """Сумма сэмплов метрики; метка path сравнивается без учёта имён параметров."""
    total = 0.0
    for sample_name, sample_labels, value in samples:
        if sample_name != name:
            continue
        if all(
            normalize_path(sample_labels.get(k, "")) == normalize_path(v)
            if k == "path"
            else sample_labels.get(k) == v
            for k, v in labels.items()
        ):
            total += value
    return total
