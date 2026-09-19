# Материалы к этапу 1. Архитектура

## Что почитать

- [Learn OpenAPI](https://learn.openapis.org/) — официальное введение в OpenAPI: структура документа, пути, операции, ответы, компоненты. Начните отсюда, прежде чем писать `openapi.yaml`.
- [Спецификация OpenAPI 3.1.0](https://spec.openapis.org/oas/v3.1.0) — справочник: когда нужно точно узнать, какие поля есть у Response Object или Parameter Object.
- [Mermaid: Sequence diagrams](https://mermaid.js.org/syntax/sequenceDiagram.html) — синтаксис диаграмм последовательности: удобно показать, что происходит при запросе к `/resource` и при изменении правил. Для схемы компонентов — [flowchart](https://mermaid.js.org/syntax/flowchart.html).
- [Redis: INCR, раздел Pattern: Rate limiter](https://redis.io/docs/latest/commands/incr/) — два способа считать запросы в окне и чем они отличаются; от этого удобно оттолкнуться при выборе алгоритма.
- [Envoy: Global rate limiting](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/other_features/global_rate_limiting) — как устроен ограничитель трафика в реальном прокси: зачем внешний сервис и общее хранилище счётчиков.
- [GitHub: Creating a repository from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) — как создать свой репозиторий из шаблона.

## Вопросы для самопроверки

1. Сколько решений «пропустить или отклонить» в секунду принимает сервис в пике? Сколько памяти займут счётчики при вашем алгоритме?
2. Чем отличаются fixed window, sliding window и token bucket? Что происходит с каждым на границе окна?
3. Почему IP клиента берётся из `X-Forwarded-For`, и почему именно первый адрес? Чем опасно доверять этому заголовку без балансировщика?
4. Как считать отклонённые запросы — увеличивают ли они счётчик? Как это меняет поведение клиента, который шлёт запросы без остановки?
5. Зачем писать `openapi.yaml` до кода, если FastAPI сгенерирует спецификацию сам?
