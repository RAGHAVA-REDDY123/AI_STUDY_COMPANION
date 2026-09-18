from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "ai_study_companion",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,        # 5 minutes max
    task_soft_time_limit=240,   # 4 minutes soft
    # In local testing without Redis container running:
    task_always_eager=settings.CELERY_ALWAYS_EAGER,
)
