# Этап 4. Наблюдаемость

## Цель

Сделать сервис наблюдаемым: по `request_id` найти в логах любой запрос, по метрикам увидеть RPS, задержки и ошибки на дашборде, описать алерты на случай, когда сервис лёг или начал сыпать ошибками.

## Что нужно сделать

Делайте по порядку и проверяйте каждый шаг, прежде чем переходить к следующему.

1. Обновите `develop` после merge этапа 3 и поднимите этап:

   ```toml
   [tool.course]
   stage = "4_observability"
   ```

2. **`X-Request-ID` и JSON-логи.** Middleware FastAPI:
   - берёт `X-Request-ID` из запроса, а если его нет — генерирует `uuid4`;
   - возвращает его в заголовке `X-Request-ID` каждого ответа;
   - пишет по одной JSON-строке на запрос в stdout с полями `timestamp`, `level`, `message`, `request_id`, `method`, `path`, `status`, `duration_ms`.

   Бизнес-события — например, «запрос отклонён» с адресом клиента — тоже пишутся в лог с `request_id`. Удобно хранить текущий `request_id` в `contextvars.ContextVar` и добавлять его в каждую запись через `logging.Filter`. Для JSON используйте `python-json-logger` — он уже в зависимостях. Access-лог uvicorn отключите (`--no-access-log`), чтобы на запрос была одна строка.

   Проверка: `curl -i -H "X-Request-ID: test-1" http://localhost:8000/health` и `docker compose logs app`.
3. **`GET /metrics`** в формате Prometheus (библиотека `prometheus-client`, уже в зависимостях):

   | Метрика | Тип | Метки |
   |---|---|---|
   | `http_requests_total` | counter | `method`, `path`, `status` |
   | `http_request_duration_seconds` | histogram | `method`, `path` |
   | `ratelimit_rejected_total` | counter | — ; растёт на каждый ответ 429 |

   Метка `path` — **шаблон маршрута**, а не сырой путь запроса. Шаблон лежит в `request.scope["route"].path` после того, как запрос обработан. Почему это важно: каждое уникальное значение метки — отдельный временной ряд в Prometheus. У ваших маршрутов нет параметров пути, но сырой путь всё равно опасен: любой сканер, перебирающий адреса, создаст по ряду на каждый адрес, и память Prometheus будет расти без предела. Запросы на несуществующие пути (сканеры, опечатки) маршрута не имеют — для них пишите в `path` одно общее значение, например `unmatched`. Объясните это своими словами в README, в разделе «Наблюдаемость».
4. **Prometheus и Grafana в compose.** Добавьте сервисы и конфиги в `observability/`:
   - `observability/prometheus/prometheus.yml`: `scrape_interval: 5s`, `rule_files: [rules.yml]` и job `app`. Экземпляров два, поэтому статический адрес `app:8000` не подойдёт — Prometheus увидит только один. Пусть он находит все адреса имени `app` через DNS:

     ```yaml
     scrape_configs:
       - job_name: app
         dns_sd_configs:
           - names: ["app"]
             type: A
             port: 8000
     ```

   - `observability/grafana/provisioning/datasources/datasources.yaml`: Prometheus (`http://prometheus:9090`, по умолчанию) и Loki (`http://loki:3100`);
   - `observability/grafana/provisioning/dashboards/dashboards.yaml`: провайдер файлов из каталога, куда смонтирован `observability/grafana/dashboards/`;
   - `observability/grafana/dashboards/app.json`: дашборд с `"uid": "app-overview"` и минимум четырьмя панелями — RPS по маршрутам, p95 времени ответа, доля ответов 5xx, отклонённые запросы `ratelimit_rejected_total` в секунду. Метрики у каждого экземпляра свои, поэтому в запросах суммируйте по экземплярам (`sum`). Пятая панель с логами из Loki приветствуется. Дашборд удобно собрать в интерфейсе Grafana, а затем сохранить его JSON через экспорт дашборда и положить в этот файл.

   Пароль администратора Grafana — из `.env`: `GRAFANA_ADMIN_PASSWORD`, логин `admin`.

   Запросы PromQL для панелей:

   ```promql
   sum by (path) (rate(http_requests_total{job="app"}[1m]))
   histogram_quantile(0.95, sum by (le, path) (rate(http_request_duration_seconds_bucket{job="app"}[5m])))
   sum(rate(http_requests_total{job="app", status=~"5.."}[5m])) / sum(rate(http_requests_total{job="app"}[5m]))
   sum(rate(ratelimit_rejected_total{job="app"}[1m]))
   ```

5. **Loki и Alloy.** Grafana Alloy находит контейнеры через Docker, читает их stdout и отправляет в Loki. Promtail не используйте: с марта 2026 года он не поддерживается.

   `observability/loki/config.yaml` — Loki в одном процессе с хранением на диске:

   ```yaml
   auth_enabled: false

   server:
     http_listen_port: 3100

   common:
     instance_addr: 127.0.0.1
     path_prefix: /loki
     storage:
       filesystem:
         chunks_directory: /loki/chunks
         rules_directory: /loki/rules
     replication_factor: 1
     ring:
       kvstore:
         store: inmemory

   schema_config:
     configs:
       - from: 2024-01-01
         store: tsdb
         object_store: filesystem
         schema: v13
         index:
           prefix: index_
           period: 24h
   ```

   `observability/alloy/config.alloy`:

   ```alloy
   discovery.docker "containers" {
     host = "unix:///var/run/docker.sock"
   }

   discovery.relabel "containers" {
     targets = discovery.docker.containers.targets

     rule {
       source_labels = ["__meta_docker_container_label_com_docker_compose_service"]
       target_label  = "service"
     }
   }

   loki.source.docker "containers" {
     host          = "unix:///var/run/docker.sock"
     targets       = discovery.relabel.containers.output
     relabel_rules = discovery.relabel.containers.rules
     forward_to    = [loki.write.local.receiver]
   }

   loki.write "local" {
     endpoint {
       url = "http://loki:3100/loki/api/v1/push"
     }
   }
   ```

   Правило `relabel` превращает имя сервиса compose в метку `service`: логи приложения — это `{service="app"}`.

   Сервису `alloy` нужен сокет Docker, смонтированный только на чтение: `/var/run/docker.sock:/var/run/docker.sock:ro`. Имейте в виду: доступ к сокету — это полный доступ к Docker хоста. Локально это нормально, в проде сокет так не монтируют без отдельной оценки рисков.
6. **Правила алертов** в `observability/prometheus/rules.yml`:
   - `AppDown`: `up{job="app"} == 0`, `for: 1m`;
   - `HighErrorRate`: доля ответов 5xx за 5 минут выше 5 %, `for: 2m`.

   Пороги можно менять, имена — нет. Проверка синтаксиса — `promtool`, команда ниже.
7. Допишите в README раздел «Наблюдаемость»: как открыть Grafana, как найти свой запрос по `request_id`, почему в `path` шаблон маршрута.
8. В `.env.example` добавьте `GRAFANA_ADMIN_PASSWORD=admin` и `LOG_LEVEL=INFO`.

## Контракт

Сервисы и порты — имена обязательны, на них завязаны тесты:

| Сервис | Имя в compose | Порт на хосте | Образ |
|---|---|---|---|
| Prometheus | `prometheus` | 9090 | `prom/prometheus:v3.13.2` |
| Grafana | `grafana` | 3000 | `grafana/grafana:13.2.2` |
| Loki | `loki` | 3100 | `grafana/loki:3.7.8` |
| Grafana Alloy | `alloy` | 12345 | `grafana/alloy:v1.19.2` |

Что проверяет CI (`contract_tests/stage_4/`, плюс все тесты этапов 2–3):

- в каждом ответе есть `X-Request-ID`, пришедший возвращается тем же;
- строка лога запроса с уникальным `X-Request-ID` появляется в Loki не позже чем через 30 секунд (CI ищет её так: `{service="app"} |= "<id>"`), и это JSON со всеми обязательными полями;
- метрики проверяются через Prometheus (каждый экземпляр отдаёт только свои): после 5 запросов `GET /limits` сумма `http_requests_total{path="/limits"}` по экземплярам выросла на 5 и больше; запрос на несуществующий путь не создаёт метку с сырым путём; есть `http_request_duration_seconds_bucket`; `ratelimit_rejected_total` растёт после ответов 429;
- в Prometheus все targets `app` в состоянии `up`, правила `AppDown` и `HighErrorRate` загружены;
- в Grafana есть дашборд `app-overview` с 4+ панелями и источники данных Prometheus и Loki;
- отдельным шагом CI — `promtool check rules observability/prometheus/rules.yml`.

## Критерии приёмки

- CI зелёный.
- В метке `path` шаблон маршрута; в README объяснено, почему.
- В логах нет секретов и тел запросов.
- У правил алертов осмысленные пороги и `for`.
- Дашборд читается без пояснений: у панелей понятные названия и единицы измерения.

## Как проверить локально

```bash
make check
make up
make test-contract
```

Проверить правила без CI:

```bash
docker run --rm -v "$PWD/observability/prometheus:/rules:ro" --entrypoint promtool prom/prometheus:v3.13.2 check rules /rules/rules.yml
```

- Prometheus: http://localhost:9090 → Status → Targets (два target `app`, оба UP), Alerts — правила.
- Grafana: http://localhost:3000, логин `admin`, пароль из `.env`. Дашборд — Dashboards → «app-overview».
- Найти запрос по `request_id`: `curl -H "X-Request-ID: find-me-1" http://localhost:8000/health`, затем в Grafana → Explore → источник Loki → запрос `{service="app"} |= "find-me-1"`.
- Alloy показывает, что он нашёл: http://localhost:12345.

## Как сдать

PR `develop → main`, reviewer `vladefr97`, сообщение в чат: «project-rate-limiter, ник, этап 4, PR готов». Подробно — в `Договоренности.md` курса.

## Типичные ошибки

- **Сырой путь в метке `path`** (`request.url.path`) — CI запросит несуществующий адрес, найдёт его в метках и упадёт.
- **Метрики не считаются для 404/422**, потому что middleware пишет метрики только при успешном ответе. Считайте в `finally`.
- **У Alloy нет доступа к сокету Docker** — в логах Alloy ошибка подключения к `/var/run/docker.sock`, в Loki пусто. Проверьте volume в compose.
- **Дашборд лежит в репозитории, но не появляется в Grafana**: нет `dashboards.yaml` или путь в нём не совпадает с тем, куда смонтирован каталог с JSON.
- **В JSON дашборда другой `uid`** — Grafana сгенерировала свой при экспорте. Поставьте `"uid": "app-overview"` руками.
- **Правило без `for`** срабатывает на единичный всплеск. `for` — сколько условие должно держаться, прежде чем алерт сработает.
- **Логи не JSON**: где-то остался `print` или стандартный формат uvicorn. Каждая строка лога приложения — один JSON-объект.
- **Prometheus не видит `app`**: в `prometheus.yml` адрес `localhost:8000`. Внутри compose сервисы обращаются друг к другу по именам.
- **Prometheus видит один экземпляр из двух**: статический `app:8000` вместо `dns_sd_configs`. Метрики второго экземпляра теряются, счётчики на дашборде занижены вдвое.
