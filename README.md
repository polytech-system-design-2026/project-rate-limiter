# Ограничитель трафика

Курс «Проектирование цифровых продуктов», СПбПУ, осень 2026.

**Студент:** <!-- впишите ФИО и группу на этапе 1 -->

Сервис защищает ресурс `/resource` двумя правилами: общим лимитом на все запросы и лимитом на каждого клиента по IP. Превысил лимит — получи 429 и подсказку, когда повторить. Правила меняются на лету, без перезапуска.

За семестр вы спроектируете его, реализуете на FastAPI и PostgreSQL, запустите в двух экземплярах за балансировщиком с общими счётчиками в Redis и измерите эффект нагрузочным тестом, а затем подключите логи, метрики, дашборд и алерты. К концу семестра у вас будет сервис, который поднимается одной командой вместе со всей инфраструктурой наблюдаемости.

Начните с [`tasks/TASK-1.md`](tasks/TASK-1.md): там пошагово, как создать репозиторий, поставить окружение и сдать первый этап.

## Этапы

| Этап | `stage` в `pyproject.toml` | Задание | Материалы |
|---|---|---|---|
| 1. Архитектура | `1_architecture` | [`tasks/TASK-1.md`](tasks/TASK-1.md) | [`materials/MATERIALS-1.md`](materials/MATERIALS-1.md) |
| 2. MVP | `2_mvp` | [`tasks/TASK-2.md`](tasks/TASK-2.md) | [`materials/MATERIALS-2.md`](materials/MATERIALS-2.md) |
| 3. Масштабирование | `3_scaling` | [`tasks/TASK-3.md`](tasks/TASK-3.md) | [`materials/MATERIALS-3.md`](materials/MATERIALS-3.md) |
| 4. Наблюдаемость | `4_observability` | [`tasks/TASK-4.md`](tasks/TASK-4.md) | [`materials/MATERIALS-4.md`](materials/MATERIALS-4.md) |
| 5. Бонус: алерты | `5_alerting` | [`tasks/TASK-5.md`](tasks/TASK-5.md) | [`materials/MATERIALS-5.md`](materials/MATERIALS-5.md) |

Этапы сдаются по порядку, каждый — отдельным pull request из `develop` в `main`. Поле `stage` говорит CI, какие проверки запускать: в начале каждого этапа поднимите его до значения из таблицы.

## Карта репозитория

| Путь | Что это | Кто редактирует |
|---|---|---|
| `tasks/`, `materials/` | задания и материалы по этапам | преподаватель |
| `docs/ARCHITECTURE.md` | архитектурный документ; часть разделов заполнена заранее | вы, с этапа 1 |
| `docs/openapi.yaml` | спецификация API | вы, с этапа 1 |
| `app/` | код сервиса: слои api / service / repository | вы, с этапа 2 |
| `tests/` | ваши тесты | вы, с этапа 2 |
| `loadtest/locustfile.py` | сценарий нагрузочного теста | вы, на этапе 3 |
| `observability/` | конфиги Prometheus, Grafana, Loki, Alloy, Alertmanager | вы, с этапа 4 |
| `contract_tests/` | эталонные тесты преподавателя | преподаватель, не редактировать |
| `.github/` | CI и шаблон pull request | преподаватель, не редактировать |
| `pyproject.toml` | зависимости, настройки линтеров, `stage` | вы: `stage`, при необходимости зависимости |
| `Makefile` | команды для разработки | можно дополнять |
| `.env.example` | пример переменных окружения | вы, с этапа 2 |

## Установка окружения

Нужны git, [uv](https://docs.astral.sh/uv/) (ставит Python 3.12 и зависимости) и Docker. Docker понадобится с этапа 2, но поставьте его сразу.

1. Поставьте uv.

   macOS и Linux:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Windows (PowerShell):

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

   Закройте и снова откройте терминал, проверьте: `uv --version`.

2. Поставьте Docker Desktop: https://docs.docker.com/get-started/get-docker/. На Linux достаточно Docker Engine с плагином compose. Проверьте: `docker compose version`.

3. В корне репозитория:

   ```bash
   make install   # ставит Python 3.12 и зависимости в .venv
   make hooks     # pre-commit: ruff и mypy перед каждым коммитом
   ```

## Проверки

| Команда | Что делает | Когда |
|---|---|---|
| `make check` | ruff, форматирование, mypy, ваши тесты — то же, что CI, кроме шагов с Docker | перед каждым пушем |
| `make check-stage-1` | проверки `docs/ARCHITECTURE.md` и `docs/openapi.yaml` | этап 1 и дальше |
| `make up` / `make down` | поднять / остановить сервис в docker compose (`down` удаляет данные) | с этапа 2 |
| `make test-contract` | контрактные тесты этапов 2…N против поднятого сервиса | с этапа 2, после `make up` |
| `make loadtest` | нагрузочный тест locust | этап 3 |
| `make format` | исправить форматирование и автоисправимые замечания ruff | когда `make check` ругается на формат |

Нет `make` (обычно на Windows) — те же команды напрямую:

| Цель | Команда |
|---|---|
| `install` | `uv sync` |
| `hooks` | `uv run pre-commit install` |
| `check` | `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy app`, `uv run pytest tests` |
| `check-stage-1` | `uv run python contract_tests/course.py test-stage-1` |
| `up` | скопируйте `.env.example` в `.env`, затем `docker compose up -d --build` |
| `down` | `docker compose down -v` |
| `test-contract` | `uv run python contract_tests/course.py test-contract` |
| `loadtest` | `uv run locust -f loadtest/locustfile.py --headless --host http://localhost:8000 --users 50 --spawn-rate 10 --run-time 1m` |
| `format` | `uv run ruff check --fix .`, `uv run ruff format .` |

Тесты, которые останавливают контейнеры, можно исключить локально: `make test-contract` аргументов не принимает, поэтому напрямую — `uv run python contract_tests/course.py test-contract -m "not restarts_containers"`.

## Что проверяет CI

CI запускается на каждый pull request и на пуш в `main`:

- `meta` — читает `stage` из `pyproject.toml`;
- `lint` — ruff, форматирование, mypy;
- `unit-tests` — ваши тесты из `tests/`;
- `stage-1-architecture` — проверки `docs/ARCHITECTURE.md` и `docs/openapi.yaml`, на всех этапах;
- `contract` — с этапа 2: поднимает сервис через docker compose и гоняет `contract_tests/stage_2` … `stage_N`, где N — ваш `stage`. Этапы, до которых вы не дошли, пропускаются.

Эталонные тесты CI берёт из шаблона, а не из вашей копии: перед запуском папка `contract_tests/` заменяется версией из шаблона. Править её у себя бессмысленно. Читать — нужно: тесты и есть точная спецификация этапа.

Если `contract` упал, откройте в логе шаг «docker compose logs»: там вывод вашего сервиса, и причина обычно видна сразу.

## Как сдавать

Работаете в ветке `develop`, сдаёте pull request `develop → main`, reviewer — `vladefr97`, в общий чат — «project-rate-limiter, ник, этап N, PR готов». PR с красным CI преподаватель не смотрит. Мержит преподаватель. Подробно — в `Договоренности.md` курса и в разделе «Как сдать» каждого задания.
