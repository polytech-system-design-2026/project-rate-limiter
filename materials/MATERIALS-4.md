# Материалы к этапу 4. Наблюдаемость

## Что почитать

- [Prometheus: Metric types](https://prometheus.io/docs/concepts/metric_types/) — counter, gauge, histogram, summary: что когда выбирать.
- [Prometheus: Histograms and summaries](https://prometheus.io/docs/practices/histograms/) — как устроена гистограмма и как посчитать p95 через `histogram_quantile`.
- [Prometheus: Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) — формат `rules.yml`, поле `for`, метки и аннотации.
- [Prometheus Python client](https://prometheus.github.io/client_python/) — `Counter`, `Histogram`, метки и отдача метрик.
- [Grafana: Provision Grafana](https://grafana.com/docs/grafana/latest/administration/provisioning/) — источники данных и дашборды из файлов, без ручной настройки в интерфейсе.
- [Grafana Alloy: loki.source.docker](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.docker/) — сбор логов контейнеров Docker в Loki; поиск по логам — [LogQL](https://grafana.com/docs/loki/latest/query/).

## Вопросы для самопроверки

1. Почему в метке `path` шаблон маршрута, а не сырой путь? Что такое кардинальность метрик и чем она опасна?
2. Как по `http_requests_total` посчитать RPS за последнюю минуту? Почему `rate()`, а не само значение счётчика?
3. Почему p95 считают по гистограмме, а не усредняют время ответа?
4. Зачем правилу `for: 1m`? Что будет без него?
5. Как по `X-Request-ID` из ответа найти все строки лога этого запроса? Зачем передавать `X-Request-ID` между сервисами?
