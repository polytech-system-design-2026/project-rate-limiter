# ABOUTME: Stage 1 checks for docs/openapi.yaml: valid OpenAPI 3.x, every contract operation present
# ABOUTME: with its required response codes, and every operation has a summary.

from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

from contract_tests.contract import STAGE_2_OPERATIONS
from contract_tests.helpers import load_openapi_yaml, normalize_path, require, spec_operations


def test_spec_is_valid_openapi_3() -> None:
    spec = load_openapi_yaml()
    version = str(spec.get("openapi", ""))
    require(
        version.startswith("3."),
        f"Поле openapi = {version!r}. Нужна спецификация OpenAPI 3.x: первая строка файла "
        "openapi: 3.1.0 (или 3.0.3).",
    )
    error = ""
    try:
        validate(spec)
    except OpenAPIValidationError as exc:
        where = " → ".join(str(p) for p in exc.absolute_path) or "корень документа"
        error = f"{exc.message}\nГде: {where}"
    require(not error, f"docs/openapi.yaml не проходит валидацию OpenAPI: {error}")


def test_contract_operations_present() -> None:
    ops = spec_operations(load_openapi_yaml())
    missing = [
        f"{m.upper()} {p}" for (m, p) in STAGE_2_OPERATIONS if (m, normalize_path(p)) not in ops
    ]
    require(
        not missing,
        "В docs/openapi.yaml не описаны операции из контракта (tasks/TASK-1.md): "
        + ", ".join(missing),
    )


def test_contract_response_codes_described() -> None:
    ops = spec_operations(load_openapi_yaml())
    problems = []
    for (method, path), codes in STAGE_2_OPERATIONS.items():
        op = ops.get((method, normalize_path(path)))
        if op is None:
            continue  # отсутствие операции проверяет test_contract_operations_present
        described = {str(code) for code in (op.get("responses") or {})}
        lacking = sorted(codes - described)
        if lacking:
            problems.append(f"{method.upper()} {path}: нет ответов {', '.join(lacking)}")
    require(
        not problems,
        "В docs/openapi.yaml описаны не все коды ответов из контракта. Ошибки — такая же "
        "часть контракта, как успешный ответ:\n  " + "\n  ".join(problems),
    )


def test_every_operation_has_summary() -> None:
    ops = spec_operations(load_openapi_yaml())
    without = [f"{m.upper()} {p}" for (m, p), op in ops.items() if not op.get("summary")]
    require(
        not without,
        "У операций нет summary (одна строка о том, что делает операция): " + ", ".join(without),
    )
