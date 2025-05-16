import logging
from functools import wraps
import datetime


def func_work_time(logger: logging.Logger = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = datetime.datetime.now(tz=datetime.timezone.utc)
            result = await func(*args, **kwargs)
            stop = datetime.datetime.now(tz=datetime.timezone.utc)
            work_time = (stop - start).total_seconds()
            logger.info(
                f"Время выполнения функции {func.__name__}: {work_time:.6f} сек"
            )
            return result

        return wrapper

    return decorator
