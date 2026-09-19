# ABOUTME: Stage 5: the Alertmanager config template renders to a valid config (amtool check-config)
# ABOUTME: and the running Alertmanager is ready and known to Prometheus.
import subprocess

import httpx
import pytest

from contract_tests.helpers import PROJECT_ROOT, eventually, require

TEMPLATE = PROJECT_ROOT / "observability" / "alertmanager" / "alertmanager.yml.tmpl"
ALERTMANAGER_IMAGE = "prom/alertmanager:v0.34.1"
FAKE_VALUES = {"TELEGRAM_BOT_TOKEN": "123456:fake-token", "TELEGRAM_CHAT_ID": "123456789"}


def render() -> str:
    require(
        TEMPLATE.exists(),
        "Не найден observability/alertmanager/alertmanager.yml.tmpl — шаблон конфига "
        "Alertmanager, см. tasks/TASK-5.md.",
    )
    text = TEMPLATE.read_text(encoding="utf-8")
    for name in FAKE_VALUES:
        require(
            "${" + name + "}" in text,
            f"В alertmanager.yml.tmpl нет подстановки ${{{name}}}. Токен и chat_id берутся "
            "из .env, в репозитории их быть не должно.",
        )
    for name, value in FAKE_VALUES.items():
        text = text.replace("${" + name + "}", value)
    return text


def test_config_is_valid() -> None:
    config = render()
    try:
        result = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-i",
                "--entrypoint",
                "sh",
                ALERTMANAGER_IMAGE,
                "-c",
                "cat > /tmp/alertmanager.yml && amtool check-config /tmp/alertmanager.yml",
            ],
            input=config,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        pytest.fail("Не найдена команда docker. Установите Docker Desktop.", pytrace=False)
    require(
        result.returncode == 0,
        "amtool check-config не принял конфиг Alertmanager (подставлены фиктивные токен и "
        f"chat_id):\n{(result.stdout + result.stderr)[-1500:]}",
    )


def test_alertmanager_ready_and_known_to_prometheus() -> None:
    def ready() -> bool:
        try:
            return httpx.get("http://localhost:9093/-/ready", timeout=5).status_code == 200
        except httpx.HTTPError:
            return False

    require(
        eventually(ready, timeout=60, interval=2),
        "Alertmanager не ответил на http://localhost:9093/-/ready. Проверьте "
        "docker compose logs alertmanager alertmanager-config.",
    )

    def known() -> bool:
        try:
            resp = httpx.get("http://localhost:9090/api/v1/alertmanagers", timeout=5)
        except httpx.HTTPError:
            return False
        return bool(resp.json().get("data", {}).get("activeAlertmanagers"))

    require(
        eventually(known, timeout=30, interval=2),
        "Prometheus не видит Alertmanager (/api/v1/alertmanagers пуст). Добавьте в "
        "prometheus.yml секцию alerting.alertmanagers с адресом alertmanager:9093.",
    )
