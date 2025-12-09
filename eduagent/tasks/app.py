from __future__ import annotations

from typing import Any, cast

from celery import Celery

from eduagent.settings import settings

celery_app = Celery(
    "eduagent",
    broker=settings.celery.broker_url,
    backend=settings.celery.result_backend,
    include=["eduagent.tasks.quiz"],
)

celery_conf = cast(Any, celery_app.conf)  # type: ignore[reportUnknownMemberType]
celery_conf.update(
    task_default_queue=settings.celery.default_queue,
    task_time_limit=settings.celery.task_time_limit,
    result_expires=settings.celery.result_expires,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

__all__ = ["celery_app"]
