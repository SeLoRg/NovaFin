from fastapi import HTTPException, Request
from functools import wraps
import logging
import grpc


def catch_errors(logger: logging.Logger = None):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                return await func(request, *args, **kwargs)

            except grpc.aio.AioRpcError as e:
                error_detail = f"Service unavailable: {e.details()}"
                logger.error(error_detail)
                request.state.error_occurred = True
                raise HTTPException(
                    status_code=503, detail=error_detail, headers={"Retry-After": "5"}
                )

            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                request.state.error_occurred = True
                raise HTTPException(status_code=500, detail="Internal server error")

        return wrapper

    return decorator
