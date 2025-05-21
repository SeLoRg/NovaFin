import grpc.aio
from fastapi import FastAPI
from getaway.app import router
from getaway.app.middleware import CookieMiddleware
from getaway.exceptions.exceptions_handlers import *

app = FastAPI(
    title="Your API",
    description="API documentation for your project",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",  # Путь для Swagger UI
    redoc_url="/api/redoc",  # Путь для Redoc UI
)

app.include_router(router, prefix="/api")
app.add_exception_handler(grpc.aio.AioRpcError, grpc_exception_handler)
app.add_exception_handler(HTTPException, httpexception_handler)
app.add_exception_handler(Exception, base_exception)
app.add_middleware(CookieMiddleware)
