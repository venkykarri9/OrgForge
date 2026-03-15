"""Celery application factory."""
from celery import Celery
from backend.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "orgforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.workers.metadata_tasks",
        "backend.workers.deploy_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
