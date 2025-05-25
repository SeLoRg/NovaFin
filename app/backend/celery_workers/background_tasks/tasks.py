from celery_workers.background_tasks import utils
from celery_workers.background_tasks.app import celery_app
import asyncio


@celery_app.task(
    name="update_currencies",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
    bind=True,
)
def update_currencies(self):
    """
    Обертка для запуска асинхронного кода в Celery
    """

    async def _async_update():
        try:
            await utils.fetch_cbr_rates()
            return "Currencies updated successfully"
        except Exception as e:
            self.retry(exc=e)

    # Запускаем асинхронный код в event loop
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_async_update())
