from urllib.parse import urlencode
from fastapi import APIRouter, Depends, Response, Request
from fastapi.responses import RedirectResponse
from common.schemas import BaseResponse
from common.gRpc.auth import auth_pb2_grpc
from getaway.app.auth import services, schemas
from getaway.Core.grpc_clients.auth_grpc_client import auth_grpc_client
from getaway.app import dependencies
from getaway.app.logger import logger
from getaway.Core.config import settings
import httpx

router = APIRouter()


@router.post("/register", response_model=BaseResponse)
async def register(
    data: schemas.RegisterRequest,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.register(data=data, auth_grpc_stub=auth_grpc_stub)


@router.post("/login", response_model=BaseResponse)
async def login(
    data: schemas.LoginRequest,
    response: Response,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.login(
        data=data, auth_grpc_stub=auth_grpc_stub, response=response
    )


@router.delete("/logout", response_model=BaseResponse)
async def logout(
    response: Response,
    request: Request,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.logout(
        response=response, request=request, auth_grpc_stub=auth_grpc_stub
    )


@router.get("/test", response_model=BaseResponse)
async def test(
    response: Response,
    request: Request,
    user_id: str = Depends(dependencies.bearer),
):
    return BaseResponse(status="success", message="Ok", detail={"user_id": user_id})


@router.post("/verify-2fa", response_model=BaseResponse)
async def verify_2fa(
    data: schemas.Verify2faRequest,
    response: Response,
    request: Request,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.verify_2fa(
        data=data, response=response, request=request, auth_grpc_stub=auth_grpc_stub
    )


@router.get("/google/login", response_class=RedirectResponse)
async def oauth_google_login(
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.oauth_google_login(auth_grpc_stub=auth_grpc_stub)


@router.get("/google/callback", response_class=RedirectResponse)
async def oauth_google_callback(
    code: str,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
):
    return await services.oauth_google_callback(
        auth_grpc_stub=auth_grpc_stub, code=code
    )
