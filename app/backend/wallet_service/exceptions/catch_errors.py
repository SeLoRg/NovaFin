import functools
import inspect
import logging
from fastapi import HTTPException
import grpc
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Type
import redis
from common.gRpc.wallet_service import wallet_pb2
from wallet_service.exceptions.exceptions import NoWallet, IdempDone, NoStripeAccount


def catch_errors(logger: Optional[logging.Logger] = None, response_class: Type = None):
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            context = bound_args.arguments.get("context")
            try:
                return await func(*args, **kwargs)
            except HTTPException as e:
                logger.error(
                    f"HTTP error in {func.__name__}: {e.status_code} - {e.detail}"
                )
                raise
            except grpc.RpcError as e:
                logger.warning(
                    f"gRPC warning in {func.__name__}: {e.code()} - {e.details()}"
                )
                raise
            except SQLAlchemyError as e:
                logger.error(f"Database error in {func.__name__}: {str(e)}")
                raise
            except redis.exceptions.RedisError as e:
                logger.error(f"Redis error in {func.__name__}: {str(e)}")
                raise

            except NoWallet as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                if context:
                    await context.abort(grpc.StatusCode.NOT_FOUND, str(e))
                raise

            except IdempDone as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                if context:
                    await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
                raise

            except NoStripeAccount as e:
                logger.error(f"Error in {func.__name__}: {str(e)}")
                if context:
                    await context.abort(grpc.StatusCode.UNAVAILABLE, str(e))
                raise

            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if context:
                    await context.abort(grpc.StatusCode.INTERNAL, str(e))
                raise

        return wrapper

    return decorator
