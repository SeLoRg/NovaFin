import grpc.aio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from getaway.app.logger import logger


async def grpc_exception_handler(
    request: Request, exc: grpc.aio.AioRpcError
) -> JSONResponse:
    logger.error(f"grpcError: {exc.details()}")

    request.state.error_occurred = True

    status_code = 503  # Service Unavailable
    if exc.code() == grpc.StatusCode.UNAUTHENTICATED:
        status_code = 401
    elif exc.code() == grpc.StatusCode.INVALID_ARGUMENT:
        status_code = 400

    return JSONResponse(
        status_code=status_code,
        content={
            "detail": f"Service error: {exc.details()}",
            "code": exc.code().name,
        },
    )


async def base_exception(request: Request, exc: Exception):
    logger.error(f"Error: {str(exc)}")
    request.state.error_occurred = True
    return JSONResponse(
        status_code=503,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "code": "503",
        },
    )
