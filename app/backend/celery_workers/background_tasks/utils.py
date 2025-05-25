import httpx

from common.Enums import ValuteCode
from common.Models import Currency
from common.crud.CrudDb import CRUD
from celery_workers.background_tasks.logger import logger
from celery_workers.background_tasks.async_database_helper import async_database_helper

crud = CRUD()


async def fetch_cbr_rates():
    logger.info("===Fetching exchange rates from CBR===")
    async with httpx.AsyncClient() as client:
        response = await client.get("https://www.cbr-xml-daily.ru/daily_json.js")
        response.raise_for_status()
        data = response.json()

        rates = {"RUB": 1.0}  # Добавим рубль как базовый
        for code, info in data["Valute"].items():
            try:
                ValuteCode(code)
                rates[code.upper()] = float(info["Value"])
            except Exception as e:
                continue

    async with async_database_helper.session_factory() as session:
        for currency, rate_to_rub in rates.items():
            if not isinstance(currency, str):
                continue
            logger.info(f"To update: {currency}: {rate_to_rub}")
            logger.info(f"Get Currency")
            currency_list = await crud.get_by_filter(
                session=session, model=Currency, code=ValuteCode(currency).value
            )
            if len(currency_list) == 0:
                logger.info(f"Currency not founded\nCreate new Currency")
                new_currency = await crud.create(
                    session=session,
                    model=Currency,
                    code=ValuteCode(currency),
                    rate_to_base=rate_to_rub,
                )
                logger.info(f"Currency created")
                continue

            logger.info(f"Currency founded\nUpdate Currency")
            await crud.update_by_id(
                session=session,
                model=Currency,
                object_id=currency_list[0].id,
                rate_to_base=rate_to_rub,
            )
            logger.info(f"Currency updated")
        await session.commit()

    logger.info(f"===CBR rates updated {rates} ===")
