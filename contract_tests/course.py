# ABOUTME: Reads [tool.course] from pyproject.toml and runs contract tests for the reached stages.
# ABOUTME: Shared by CI, Makefile and the no-make commands in README; do not edit, CI replaces it.
"""Точка входа курса: какой этап объявлен и какие контрактные тесты гонять.

Использование:
    python contract_tests/course.py stage-number    # печатает номер этапа (1–5)
    python contract_tests/course.py test-stage-1    # проверки этапа 1, без Docker
    python contract_tests/course.py test-contract   # этапы 2..N против поднятого сервиса
"""

import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTRACT_DIR = PROJECT_ROOT / "contract_tests"
PYTEST_INI = CONTRACT_DIR / "pytest.ini"

STAGES = {
    "1_architecture": 1,
    "2_mvp": 2,
    "3_scaling": 3,
    "4_observability": 4,
    "5_alerting": 5,
}
TOPICS = ("url-shortener", "autocomplete", "rate-limiter")


class CourseConfigError(Exception):
    """Секция [tool.course] в pyproject.toml заполнена неверно."""


@dataclass(frozen=True)
class Course:
    topic: str
    stage: str

    @property
    def stage_number(self) -> int:
        return STAGES[self.stage]


def read_course(pyproject: Path = PROJECT_ROOT / "pyproject.toml") -> Course:
    if not pyproject.exists():
        raise CourseConfigError(f"Не найден {pyproject}. Запускайте команды из корня репозитория.")
    with pyproject.open("rb") as f:
        try:
            data = tomllib.load(f)
        except tomllib.TOMLDecodeError as exc:
            raise CourseConfigError(
                f"pyproject.toml не читается как TOML: {exc}. Проверьте кавычки и скобки."
            ) from exc
    section = data.get("tool", {}).get("course")
    if not isinstance(section, dict):
        raise CourseConfigError(
            "В pyproject.toml нет секции [tool.course]. Верните её из шаблона: "
            'topic = "<тема>" и stage = "1_architecture".'
        )
    topic = section.get("topic")
    stage = section.get("stage")
    if topic not in TOPICS:
        raise CourseConfigError(
            f"[tool.course].topic = {topic!r}, а должно быть одно из: {', '.join(TOPICS)}. "
            "Поле topic задано в шаблоне, его менять не нужно."
        )
    if stage not in STAGES:
        raise CourseConfigError(
            f"[tool.course].stage = {stage!r}, а должно быть одно из: {', '.join(STAGES)}. "
            "Впишите значение текущего этапа из tasks/TASK-N.md, в кавычках."
        )
    return Course(topic=topic, stage=stage)


def contract_dirs(stage_number: int) -> list[str]:
    """Папки контрактных тестов всех достигнутых этапов, начиная со второго."""
    return [str(CONTRACT_DIR / f"stage_{n}") for n in range(2, stage_number + 1)]


def run_pytest(paths: list[str], extra: list[str]) -> int:
    # Свой pytest.ini: настройки pytest из pyproject.toml и conftest.py вне
    # contract_tests/ на эталонные тесты не влияют.
    cmd = [sys.executable, "-m", "pytest", "-c", str(PYTEST_INI), *paths, *extra]
    return subprocess.call(cmd, cwd=PROJECT_ROOT)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    command, extra = argv[0], argv[1:]
    try:
        course = read_course()
    except CourseConfigError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1

    if command == "stage-number":
        print(course.stage_number)
        return 0
    if command == "test-stage-1":
        return run_pytest([str(CONTRACT_DIR / "stage_1")], extra)
    if command == "test-contract":
        if course.stage_number < 2:
            print(
                f"Сейчас stage = {course.stage!r}: на этапе 1 сервиса ещё нет, "
                "контрактных тестов по HTTP нет. Запустите make check-stage-1."
            )
            return 0
        print(
            f"Этап {course.stage}: гоняю contract_tests/stage_2 … stage_{course.stage_number}",
            flush=True,
        )
        return run_pytest(contract_dirs(course.stage_number), extra)

    print(f"Неизвестная команда {command!r}.\n{__doc__}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
