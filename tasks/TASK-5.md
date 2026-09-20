# Этап 5 (бонус). Алерты в Telegram

## Цель

Довести алерты до человека: когда сервис лёг, Alertmanager присылает сообщение в Telegram. Этап нужен для оценки «5».

## Что нужно сделать

1. Обновите `develop` после merge этапа 4 и поднимите этап:

   ```toml
   [tool.course]
   stage = "5_alerting"
   ```

2. **Создайте бота.** В Telegram откройте [@BotFather](https://t.me/BotFather), отправьте `/newbot`, придумайте имя и username (должен оканчиваться на `bot`). BotFather пришлёт токен вида `123456789:AA...` — это пароль бота, никому его не показывайте.
3. **Узнайте `chat_id`.** Напишите своему боту любое сообщение, затем откройте в браузере:

   ```
   https://api.telegram.org/bot<токен>/getUpdates
   ```

   В ответе найдите `"chat":{"id":123456789,...}` — это `chat_id`. Для группы добавьте бота в группу и напишите в неё; `chat_id` группы отрицательный.
4. **Токен и `chat_id` — только в `.env`:**

   ```
   TELEGRAM_BOT_TOKEN=123456789:AA...
   TELEGRAM_CHAT_ID=123456789
   ```

   В `.env.example` — фиктивные значения того же формата, их использует CI: `TELEGRAM_BOT_TOKEN=000000000:replace-me`, `TELEGRAM_CHAT_ID=123456789`. `chat_id` должен быть ненулевым числом, иначе Alertmanager не запустится.
5. **Шаблон конфига** `observability/alertmanager/alertmanager.yml.tmpl`:

   ```yaml
   route:
     receiver: telegram
     group_by: ["alertname"]
     group_wait: 10s
     repeat_interval: 1h

   receivers:
     - name: telegram
       telegram_configs:
         - bot_token: "${TELEGRAM_BOT_TOKEN}"
           chat_id: ${TELEGRAM_CHAT_ID}
           send_resolved: true
   ```

6. **Рендер конфига при старте.** Alertmanager не подставляет переменные окружения в свой конфиг. Поэтому до его запуска одноразовый контейнер вписывает значения из `.env` в шаблон и кладёт готовый файл в общий volume:

   ```yaml
   services:
     alertmanager-config:
       image: alpine:3.22
       env_file: .env
       volumes:
         - ./observability/alertmanager:/templates:ro
         - alertmanager-config:/config
       command:
         - sh
         - -c
         - >-
           sed -e "s|\$${TELEGRAM_BOT_TOKEN}|$${TELEGRAM_BOT_TOKEN}|g"
           -e "s|\$${TELEGRAM_CHAT_ID}|$${TELEGRAM_CHAT_ID}|g"
           /templates/alertmanager.yml.tmpl > /config/alertmanager.yml

     alertmanager:
       image: prom/alertmanager:v0.34.1
       command: ["--config.file=/config/alertmanager.yml"]
       volumes:
         - alertmanager-config:/config:ro
       ports:
         - "9093:9093"
       depends_on:
         alertmanager-config:
           condition: service_completed_successfully

   volumes:
     alertmanager-config:
   ```

   `$$` в compose — экранирование: compose не подставляет переменную сам, а передаёт `$` в команду внутри контейнера. `service_completed_successfully` — `alertmanager` стартует только после того, как рендер завершился без ошибки.
7. **Prometheus должен знать об Alertmanager** — добавьте в `observability/prometheus/prometheus.yml`:

   ```yaml
   alerting:
     alertmanagers:
       - static_configs:
           - targets: ["alertmanager:9093"]
   ```

8. **Проверьте руками:**

   ```bash
   make up
   docker compose stop app
   ```

   Остановятся оба экземпляра. Через 1–3 минуты (`for: 1m` у `AppDown`, интервал опроса Prometheus и `group_wait`) бот пришлёт сообщение. Сделайте скриншот. Затем `docker compose start app` — придёт сообщение, что алерт снят (resolved).

## Контракт

| Сервис | Имя в compose | Порт на хосте |
|---|---|---|
| Alertmanager | `alertmanager` | 9093 |

Что проверяет CI (`contract_tests/stage_5/`, плюс все тесты этапов 2–4):

- шаблон `observability/alertmanager/alertmanager.yml.tmpl` содержит `${TELEGRAM_BOT_TOKEN}` и `${TELEGRAM_CHAT_ID}`; после подстановки фиктивных значений `amtool check-config` принимает конфиг;
- Alertmanager отвечает на `http://localhost:9093/-/ready`;
- Prometheus видит активный Alertmanager (`/api/v1/alertmanagers`).

Реальную отправку в Telegram CI не проверяет — для этого скриншот.

## Критерии приёмки

- CI зелёный.
- В описании PR скриншот сообщения бота о сработавшем `AppDown`.
- Токена бота нет в репозитории — ни в коде, ни в истории коммитов.

## Как проверить локально

```bash
make check
make up
make test-contract
```

- Alertmanager: http://localhost:9093 — активные алерты.
- Prometheus: http://localhost:9090 → Alerts — состояние правил (inactive → pending → firing).
- Готовый конфиг внутри контейнера: `docker compose exec alertmanager cat /config/alertmanager.yml`.

## Как сдать

PR `develop → main`, reviewer `vladefr97`, скриншот сообщения бота — в описании PR. Сообщение в чат: «project-rate-limiter, ник, этап 5, PR готов». Подробно — в [README](../README.md#как-сдавать), раздел «Как сдавать».

## Типичные ошибки

- **Токен закоммичен.** Перевыпустите токен бота в @BotFather — старый перестанет работать. Удаление файла следующим коммитом не помогает: токен остаётся в истории.
- **Prometheus не знает об Alertmanager** — алерт горит в Prometheus (firing), но сообщения нет. Проверьте секцию `alerting` в `prometheus.yml`.
- **Бот не может написать в чат** — вы не написали боту первым или не добавили его в группу.
- **Alertmanager падает при старте с ошибкой «missing chat_id»** — в `.env` `TELEGRAM_CHAT_ID` пустой или 0.
- **Опечатка в ключе конфига** (`send_resolvd`) — `amtool check-config` в CI покажет строку и имя поля.
- **Сообщения нет через минуту** — у `AppDown` `for: 1m`, плюс интервал опроса Prometheus и `group_wait`. Подождите 2–3 минуты и смотрите статус алерта в Prometheus.
