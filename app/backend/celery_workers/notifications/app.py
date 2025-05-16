from celery import Celery

celery_app = Celery(
    "notifications",
    broker="redis://redis:6379/3",
    backend="redis://redis:6379/3",
    broker_connection_retry_on_startup=True,
)


celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)
