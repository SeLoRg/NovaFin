import functools
import inspect
import logging
from fastapi import HTTPException
import grpc
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Type
import redis
from common.gRpc.auth import auth_pb2


def catch_errors(logger: Optional[logging.Logger] = None, response_class: Type = None):
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            exception: Exception = None
            try:
                return await func(*args, **kwargs)
            except HTTPException as e:
                logger.error(
                    f"HTTP error in {func.__name__}: {e.status_code} - {e.detail}"
                )
            except grpc.RpcError as e:
                logger.warning(
                    f"gRPC warning in {func.__name__}: {e.code()} - {e.details()}"
                )
                if response_class:
                    return response_class(
                        meta=auth_pb2.BaseResponse(status="error", message=str(e))
                    )
            except SQLAlchemyError as e:
                logger.error(f"Database error in {func.__name__}: {str(e)}")
                if response_class:
                    return response_class(
                        meta=auth_pb2.BaseResponse(status="error", message=str(e))
                    )
            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error in {func.__name__}: {str(e)}")
                if response_class:
                    return response_class(
                        meta=auth_pb2.BaseResponse(status="error", message=str(e))
                    )
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if response_class:
                    return response_class(
                        meta=auth_pb2.BaseResponse(status="error", message=str(e))
                    )

        return wrapper

    return decorator
