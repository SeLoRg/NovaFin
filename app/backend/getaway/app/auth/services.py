import json

import grpc
from fastapi import Response, Request
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from getaway.app.auth import schemas
from common.gRpc.auth import auth_pb2, auth_pb2_grpc
from common.schemas import BaseResponse
from getaway.app.logger import logger
from getaway.exceptions.catch_errors import catch_errors
from getaway.Core.config import settings
from getaway.app import utils


@catch_errors(logger=logger)
async def register(
    data: schemas.RegisterRequest,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
) -> BaseResponse:
    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    request = auth_pb2.RegistrateRequest(login=data.login, password=data.password)
    response: auth_pb2.RegistrateResponse = await auth_grpc_stub.Registrate(
        request=request
    )

    return BaseResponse(status=response.meta.status, message=response.meta.message)


async def login(
    data: schemas.LoginRequest,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
    response: Response,
) -> BaseResponse:
    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    request = auth_pb2.LoginRequest(user_email=data.login, password=data.password)
    result: auth_pb2.LoginResponse = await auth_grpc_stub.Login(request=request)
    response_body = BaseResponse(status=result.meta.status, message=result.meta.message)
    response_body.detail = utils.parse_grpc_detail(result.meta.detail)

    tokens = response_body.detail.get("tokens")

    if tokens is not None:
        response.set_cookie(
            key=settings.JWT_ACCESS_COOKIE,
            value=tokens.get("jwt_access"),
            httponly=True,
            max_age=settings.ACCESS_MAX_AGE_COOKIE_S,
        )
        response.set_cookie(
            key=settings.JWT_REFRESH_COOKIE,
            value=tokens.get("jwt_refresh"),
            httponly=True,
            max_age=settings.REFRESH_MAX_AGE_COOKIE_S,
        )

    return response_body


async def logout(
    request: Request,
    response: Response,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
) -> BaseResponse:
    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    jwt_access = request.cookies.get(settings.JWT_ACCESS_COOKIE)
    jwt_refresh = request.cookies.get(settings.JWT_REFRESH_COOKIE)

    if jwt_access is None or jwt_refresh is None:
        return BaseResponse(status="success", message="User logout success.")

    req: auth_pb2.LogoutRequest = auth_pb2.LogoutRequest(
        jwt_access=jwt_access, jwt_refresh=jwt_refresh
    )
    res: auth_pb2.LogoutResponse = await auth_grpc_stub.Logout(request=req)
    response_body: BaseResponse = BaseResponse(
        status=res.meta.status, message=res.meta.message
    )
    response_body.detail = utils.parse_grpc_detail(res.meta.detail)

    response.delete_cookie(key=settings.JWT_ACCESS_COOKIE)
    response.delete_cookie(key=settings.JWT_REFRESH_COOKIE)

    return response_body


async def verify_2fa(
    data: schemas.Verify2faRequest,
    request: Request,
    response: Response,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
) -> BaseResponse:
    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    req: auth_pb2.Verify2faRequest = auth_pb2.Verify2faRequest(
        user_id=data.user_id, opt_code=data.opt_code
    )
    res: auth_pb2.Verify2faResponse = await auth_grpc_stub.Verify_2fa(request=req)
    response_body: BaseResponse = BaseResponse(
        status=res.meta.status, message=res.meta.message
    )
    response_body.detail = utils.parse_grpc_detail(res.meta.detail)

    tokens = response_body.detail.get("tokens")

    if tokens is not None:
        response.set_cookie(
            key=settings.JWT_ACCESS_COOKIE,
            value=tokens.get("jwt_access"),
            httponly=True,
            max_age=settings.ACCESS_MAX_AGE_COOKIE_S,
        )
        response.set_cookie(
            key=settings.JWT_REFRESH_COOKIE,
            value=tokens.get("jwt_refresh"),
            httponly=True,
            max_age=settings.REFRESH_MAX_AGE_COOKIE_S,
        )

    return response_body


async def oauth_google_login(
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
) -> RedirectResponse:
    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    req = auth_pb2.GetGoogleAuthUrlRequest()
    res = await auth_grpc_stub.Get_google_auth_url(req)

    detail = utils.parse_grpc_detail(res.meta.detail)

    if redirect_url := detail.get("redirect_url"):
        return RedirectResponse(redirect_url)

    raise grpc.RpcError("redirect_url not founded")


async def oauth_google_callback(
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None,
    code: str,
) -> RedirectResponse:

    if auth_grpc_stub is None:
        raise HTTPException(status_code=500, detail=f"Auth service is not available")

    req = auth_pb2.HandleGoogleCallbackRequest(code=code)
    res = await auth_grpc_stub.Handle_google_callback(req)

    detail = utils.parse_grpc_detail(res.meta.detail)
    redirect_response = RedirectResponse(url="/")
    if tokens := detail.get("tokens"):
        redirect_response.set_cookie(
            key=settings.JWT_ACCESS_COOKIE,
            value=tokens.get("jwt_access"),
            httponly=True,
            max_age=settings.ACCESS_MAX_AGE_COOKIE_S,
        )
        redirect_response.set_cookie(
            key=settings.JWT_REFRESH_COOKIE,
            value=tokens.get("jwt_refresh"),
            httponly=True,
            max_age=settings.REFRESH_MAX_AGE_COOKIE_S,
        )
        return redirect_response

    raise HTTPException(status_code=400, detail="Tokens not found in response")
