from fastapi import HTTPException, Request
from functools import wraps
import logging
import grpc


def catch_errors(logger: logging.Logger = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)

            except grpc.aio.AioRpcError as e:
                error_detail = f"Service unavailable: {e.details()}"
                logger.error(error_detail)
                raise

            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator
