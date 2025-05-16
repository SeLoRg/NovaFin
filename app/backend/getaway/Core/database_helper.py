from app.backend.common.Core.Database import Database
from app.backend.getaway.Core.config import settings

async_database_helper = Database(url=settings.postgres_url, echo=False)
