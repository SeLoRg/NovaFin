from common.Core.Database import Database
from wallet_service.Core.config import settings

async_database_helper = Database(url=settings.postgres_url, echo=False)
