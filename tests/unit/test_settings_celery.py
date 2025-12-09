from eduagent.settings import CeleryConfig, Settings

CUSTOM_TASK_TIME_LIMIT = 123


def test_settings_celery_uses_rabbitmq_defaults() -> None:
    config = Settings()
    assert config.celery.broker_url == config.rabbitmq.amqp_url
    assert config.celery.result_backend == config.database.celery_result_backend
    assert config.celery.default_queue == "eduagent.quizzes"


def test_settings_celery_respects_overrides() -> None:
    explicit = CeleryConfig(
        broker_url="amqp://demo//",
        result_backend="db+postgresql+psycopg://demo",
        default_queue="custom.queue",
        task_time_limit=CUSTOM_TASK_TIME_LIMIT,
    )
    config = Settings(celery=explicit)
    assert config.celery.broker_url == "amqp://demo//"
    assert config.celery.result_backend == "db+postgresql+psycopg://demo"
    assert config.celery.default_queue == "custom.queue"
    assert config.celery.task_time_limit == CUSTOM_TASK_TIME_LIMIT
