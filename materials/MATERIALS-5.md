# Материалы к этапу 5. Алерты в Telegram

## Что почитать

- [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) — что делает Alertmanager: группировка, подавление, маршрутизация алертов.
- [Alertmanager: Configuration](https://prometheus.io/docs/alerting/latest/configuration/) — формат конфига, `route`, `receivers` и раздел `telegram_config`.
- [Telegram: From BotFather to 'Hello World'](https://core.telegram.org/bots/tutorial) — как создать бота и получить токен.
- [Telegram Bot API](https://core.telegram.org/bots/api) — метод `getUpdates`, из ответа которого берётся `chat_id`.
- [Compose: depends_on](https://docs.docker.com/reference/compose-file/services/) — условие `service_completed_successfully` для одноразового контейнера, который рендерит конфиг.

## Вопросы для самопроверки

1. Чем отличаются задачи Prometheus и Alertmanager? Почему правила живут в Prometheus, а отправка — в Alertmanager?
2. Через сколько времени после `docker compose stop app` придёт сообщение? Из чего складывается задержка?
3. Зачем `group_by` и `repeat_interval`? Что будет, если упадут сразу десять сервисов?
4. Почему токен бота нельзя коммитить, даже в приватный репозиторий? Что делать, если это случилось?
5. Почему Alertmanager не подставляет переменные окружения сам и как это обходит ваш compose?
