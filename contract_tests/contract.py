# ABOUTME: API contract of the topic as data: operations and status codes the service must provide.
# ABOUTME: Stage 1 checks docs/openapi.yaml against it; stage 2+ tests exercise it over HTTP.

# Операции этапа 2 (docs/openapi.yaml пишется под них на этапе 1):
# (метод, путь) -> коды ответов, которые обязательно описаны в спецификации.
STAGE_2_OPERATIONS: dict[tuple[str, str], set[str]] = {
    ("get", "/resource"): {"200", "429"},
    ("get", "/limits"): {"200"},
    ("put", "/limits"): {"200", "422"},
    ("get", "/health"): {"200", "503"},
}

# Длина docs/ARCHITECTURE.md в шаблоне без строк «> TODO:» и вводного абзаца —
# то, что остаётся от шаблона в заполненном документе. Сам документ должен быть
# длиннее этой базы хотя бы на ARCHITECTURE_MIN_ADDED символов без пробельных.
ARCHITECTURE_TEMPLATE_LENGTH = 2674
ARCHITECTURE_MIN_ADDED = 1500
