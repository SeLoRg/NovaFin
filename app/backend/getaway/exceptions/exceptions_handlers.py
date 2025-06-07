import grpc.aio
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from getaway.app.logger import logger


async def grpc_exception_handler(
    request: Request, exc: grpc.aio.AioRpcError
) -> JSONResponse:
    logger.error(f"grpcError: {exc.details()}")

    grpc_to_http_status = {
        grpc.StatusCode.UNAUTHENTICATED.name: 401,
        grpc.StatusCode.INVALID_ARGUMENT.name: 400,
        grpc.StatusCode.NOT_FOUND.name: 404,
        grpc.StatusCode.UNAVAILABLE.name: 422,
    }
    status_code = grpc_to_http_status.get(exc.code().name, 503)  # Service Unavailable

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


async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
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
