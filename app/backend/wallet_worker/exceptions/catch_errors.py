import asyncio
import functools
import inspect
import json
import logging
from fastapi import HTTPException
import grpc
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Type
import redis
from common.gRpc.auth import auth_pb2
from common.schemas import BaseResponse, WalletTransactionRequest
from wallet_worker.Core.async_kafka_client import async_kafka_client


def catch_errors(logger: Optional[logging.Logger] = None):
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except SQLAlchemyError as e:
                logger.error(f"Database error in {func.__name__}: {str(e)}")
            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error in {func.__name__}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            except (KeyboardInterrupt, SystemExit, asyncio.CancelledError):
                raise

        return wrapper

    return decorator
