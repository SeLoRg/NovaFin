from fastapi import FastAPI, Request, Response, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from getaway.Core.config import settings
from getaway.app.logger import logger
from getaway.exceptions.catch_errors import catch_errors


# 1. Middleware для обработки Response ПОСЛЕ эндпоинта
class CookieMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("---Middleware before---")
        logger.info(f"---Func {call_next.__name__}---")
        response = await call_next(request)  # Сначала выполняем эндпоинт
        logger.info(f"--Middleware after--")

        if hasattr(request.state, "error_occurred"):
            return response

        if hasattr(request.state, "new_tokens"):
            logger.info(f"Устанавливаем куки...")
            response.set_cookie(
                key=settings.JWT_ACCESS_COOKIE,
                value=request.state.new_tokens[settings.JWT_ACCESS_COOKIE],
                max_age=settings.ACCESS_MAX_AGE_COOKIE_S,
                httponly=True,
                samesite="lax",
            )
            response.set_cookie(
                key=settings.JWT_REFRESH_COOKIE,
                value=request.state.new_tokens[settings.JWT_REFRESH_COOKIE],
                max_age=settings.REFRESH_MAX_AGE_COOKIE_S,
                httponly=True,
                samesite="lax",
            )
            logger.info(f"Куки установлены")

        if getattr(request.state, "clear_cookies", False):
            logger.info(f"Удаляем куки")
            response.delete_cookie(settings.JWT_ACCESS_COOKIE)
            response.delete_cookie(settings.JWT_REFRESH_COOKIE)
            logger.info(f"Куки удалены")

        return response
