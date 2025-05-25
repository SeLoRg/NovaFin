from common.Core.Database import Database
from celery_workers.background_tasks.config import settings

async_database_helper = Database(url=settings.postgres_url, echo=False)
