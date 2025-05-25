import grpc.aio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from getaway.app.logger import logger


async def grpc_exception_handler(
    request: Request, exc: grpc.aio.AioRpcError
) -> JSONResponse:
    logger.error(f"grpcError: {exc.details()}")

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
    return JSONResponse(
        status_code=503,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "code": "503",
        },
    )


async def httpexception_handler(request: Request, exc: HTTPException):
    logger.error(f"Error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": exc.status_code,
        },
    )
