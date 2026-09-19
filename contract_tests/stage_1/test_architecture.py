# ABOUTME: Stage 1 checks for docs/ARCHITECTURE.md: required sections in order, mermaid diagram,
# ABOUTME: no TODO placeholders left, and enough text added on top of the template.
import re
from pathlib import Path

import pytest

from contract_tests.contract import ARCHITECTURE_MIN_ADDED, ARCHITECTURE_TEMPLATE_LENGTH
from contract_tests.helpers import require

ARCHITECTURE = Path(__file__).resolve().parents[2] / "docs" / "ARCHITECTURE.md"

REQUIRED_SECTIONS = [
    "Сценарии",
    "Функциональные требования",
    "Нефункциональные требования",
    "Контракт API",
    "Модель данных",
    "Компоненты и потоки данных",
    "Выбор хранилища",
]

FENCE = re.compile(r"^\s*(```|~~~)")


def read_architecture() -> str:
    if not ARCHITECTURE.exists():
        pytest.fail(
            "Не найден docs/ARCHITECTURE.md. Верните файл из шаблона и заполните его "
            "(tasks/TASK-1.md).",
            pytrace=False,
        )
    return ARCHITECTURE.read_text(encoding="utf-8")


def headings_outside_code(text: str) -> list[str]:
    headings = []
    in_code = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_code = not in_code
            continue
        if not in_code and line.startswith("## "):
            headings.append(line[3:].strip())
    return headings


def test_required_sections_in_order() -> None:
    headings = headings_outside_code(read_architecture())
    missing = [s for s in REQUIRED_SECTIONS if s not in headings]
    require(
        not missing,
        "В docs/ARCHITECTURE.md нет обязательных разделов: "
        + ", ".join(f"«## {s}»" for s in missing)
        + ". Заголовки второго уровня должны совпадать с шаблоном дословно.",
    )
    positions = [headings.index(s) for s in REQUIRED_SECTIONS]
    require(
        positions == sorted(positions),
        "Разделы docs/ARCHITECTURE.md идут не в том порядке. Нужен такой: "
        + " → ".join(REQUIRED_SECTIONS)
        + ". Свои разделы можно добавлять между ними.",
    )


def test_has_mermaid_diagram() -> None:
    text = read_architecture()
    require(
        re.search(r"^\s*```mermaid\s*$", text, re.MULTILINE),
        "В docs/ARCHITECTURE.md нет схемы: добавьте в раздел «Компоненты и потоки данных» "
        "блок ```mermaid с flowchart или sequenceDiagram (см. materials/MATERIALS-1.md).",
    )


def test_no_todo_left() -> None:
    text = read_architecture()
    todo_lines = [
        f"строка {n}: {line.strip()[:80]}"
        for n, line in enumerate(text.splitlines(), start=1)
        if line.lstrip().startswith("> TODO:")
    ]
    require(
        not todo_lines,
        f"В docs/ARCHITECTURE.md остались незаполненные места с «> TODO:» ({len(todo_lines)}). "
        "Замените каждое своим текстом и удалите строку с TODO:\n  " + "\n  ".join(todo_lines),
    )


def test_enough_content_added() -> None:
    text = read_architecture()
    length = len(re.sub(r"\s", "", text))
    required = ARCHITECTURE_TEMPLATE_LENGTH + ARCHITECTURE_MIN_ADDED
    require(
        length >= required,
        f"docs/ARCHITECTURE.md слишком короткий: {length} символов без пробелов, "
        f"нужно хотя бы {required} (шаблон + {ARCHITECTURE_MIN_ADDED} ваших). "
        "Скорее всего, какой-то раздел заполнен одной строкой — раскройте расчёты и решения.",
    )
