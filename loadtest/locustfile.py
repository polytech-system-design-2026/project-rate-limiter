# ABOUTME: Load test scenario for stage 3, run with `make loadtest` against the running service.
# ABOUTME: Fill in the tasks as described in tasks/TASK-3.md before measuring.
from locust import HttpUser, between


class ServiceUser(HttpUser):
    """Пользователь сервиса. Задачи (@task) добавляете на этапе 3 по tasks/TASK-3.md."""

    wait_time = between(0.1, 0.5)
