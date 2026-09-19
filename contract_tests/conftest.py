# ABOUTME: Shared fixtures for teacher's contract tests: HTTP client and service readiness wait.
# ABOUTME: Do not edit — CI replaces contract_tests/ with the template copy at tag reference-v1.
"""Контрактные тесты преподавателя. Не редактировать.

CI перед прогоном заменяет всю папку contract_tests/ копией из шаблона
по тегу reference-v1 (см. .github/workflows/ci.yml), правки здесь на
результат не влияют.
"""

import os
from collections.abc import Iterator

import httpx
import pytest

from contract_tests.helpers import wait_until_healthy

BASE_URL = os.environ.get("APP_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        wait_until_healthy(c)
        yield c
