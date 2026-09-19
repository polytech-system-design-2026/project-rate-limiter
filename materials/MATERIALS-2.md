# Материалы к этапу 2. MVP

## Что почитать

- [FastAPI: Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/) — `HTTPException`, коды ответов и формат `{"detail": ...}`, ошибки валидации 422.
- [MDN: 429 Too Many Requests](https://developer.mozilla.org/ru/docs/Web/HTTP/Reference/Status/429) и [Retry-After](https://developer.mozilla.org/ru/docs/Web/HTTP/Reference/Headers/Retry-After) — что означает ответ и как клиент понимает, когда повторить. На русском.
- [MDN: X-Forwarded-For](https://developer.mozilla.org/ru/docs/Web/HTTP/Reference/Headers/X-Forwarded-For) — формат заголовка и почему первый адрес — клиентский. На русском.
- [SQLAlchemy 2.0: ORM Quick Start](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) — модели через `Mapped` и `mapped_column`, сессия, `select`.
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) — `alembic init`, первая миграция, `upgrade head`.
- [Docker Compose: Control startup order](https://docs.docker.com/compose/how-tos/startup-order/) — `healthcheck` и `depends_on` с `condition: service_healthy`, чтобы сервис не стартовал раньше базы.

## Вопросы для самопроверки

1. Как ваш алгоритм считает `retry_after`? Почему он не может быть больше размера окна?
2. Что произойдёт с правилами, если при старте всегда записывать значения из `.env`?
3. Почему `/health` должен ходить в базу, а не просто возвращать 200?
4. Почему счётчики в памяти процесса работают на этапе 2 и перестанут работать на этапе 3?
5. Что делает каждый из трёх слоёв api / service / repository и где должно жить определение IP клиента?
