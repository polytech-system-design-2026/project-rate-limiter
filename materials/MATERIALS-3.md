# Материалы к этапу 3. Масштабирование

## Что почитать

- [Redis: Scripting with Lua](https://redis.io/docs/latest/develop/interact/programmability/eval-intro/) — `EVAL` и скрипты, которые выполняются атомарно: проверить счётчик и увеличить его одной операцией.
- [Redis Sorted sets](https://redis.io/docs/latest/develop/data-types/sorted-sets/) — упорядоченные множества: основа sliding window log (score — время запроса).
- [nginx: Using nginx as HTTP load balancer](https://nginx.org/en/docs/http/load_balancing.html) — `upstream` и распределение запросов между экземплярами.
- [nginx: ngx_http_proxy_module](https://nginx.org/en/docs/http/ngx_http_proxy_module.html) — `proxy_pass`, `proxy_set_header` и переменная `$proxy_add_x_forwarded_for`.
- [Compose: deploy](https://docs.docker.com/reference/compose-file/deploy/) — `replicas`: несколько экземпляров одного сервиса.
- [Locust: Running without the web UI](https://docs.locust.io/en/stable/running-without-web-ui.html) — запуск `--headless` с параметрами `--users`, `--spawn-rate`, `--run-time`.

## Вопросы для самопроверки

1. Почему проверку счётчика и его увеличение нельзя делать двумя отдельными командами Redis? Нарисуйте последовательность, при которой пройдёт лишний запрос.
2. Как nginx узнаёт адреса обоих экземпляров? Что будет, если один экземпляр упадёт?
3. Почему миграции нельзя запускать из обоих экземпляров при старте?
4. Как экземпляры узнают об изменении правил через `PUT /limits`, пришедшем в другой экземпляр?
5. Что показал нагрузочный тест: во что упирается RPS — в сервис, Redis или генератор нагрузки?
