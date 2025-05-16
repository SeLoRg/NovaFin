from fastapi import Request, Response, HTTPException, Depends
from common.gRpc.auth import auth_pb2_grpc, auth_pb2
from common.gRpc.wallet_service import wallet_pb2_grpc
from common.schemas import BaseResponse
from getaway.Core.config import settings
from getaway.Core.grpc_clients.auth_grpc_client import auth_grpc_client
from getaway.Core.grpc_clients.wallet_grpc_client import wallet_grpc_client
from getaway.app import utils
from getaway.app.logger import logger
from typing import Annotated


async def bearer(
    request: Request,
    auth_grpc_stub: auth_pb2_grpc.AuthServiceStub | None = Depends(
        auth_grpc_client.get_stub
    ),
) -> str:
    try:
        jwt_access = request.cookies.get(settings.JWT_ACCESS_COOKIE)
        jwt_refresh = request.cookies.get(settings.JWT_REFRESH_COOKIE)

        exc = HTTPException(status_code=401, detail="Authentication failed")

        if jwt_access is None or jwt_refresh is None:
            raise exc

        if auth_grpc_stub is None:
            raise Exception("Auth service is unavailable")

        # 1. Проверяем access токен
        grpc_request = auth_pb2.CheckAccessRequest(jwt_access=jwt_access)
        res = await auth_grpc_stub.CheckAccess(grpc_request)

        response_body = BaseResponse(
            status=res.meta.status,
            message=res.meta.message,
            detail=utils.parse_grpc_detail(res.meta.detail),
        )
        logger.info(f"Ответ от CheckAccessRequest: {response_body.model_dump()}")

        if response_body.status == "success":
            return response_body.detail.get("payload").get("user_id")

        # 2. Обновляем токены
        grpc_request = auth_pb2.GetNewTokensRequest(
            jwt_refresh=jwt_refresh,
            jwt_access=jwt_access,
        )
        res = await auth_grpc_stub.GetNewTokens(grpc_request)

        response_body = BaseResponse(
            status=res.meta.status,
            message=res.meta.message,
            detail=utils.parse_grpc_detail(res.meta.detail),
        )
        logger.info(f"Ответ от GetNewTokensRequest: {response_body.model_dump()}")

        if response_body.status != "success":
            request.state.clear_cookies = True
            raise exc

        tokens = response_body.detail.get("tokens")
        new_access = tokens.get("jwt_access")
        new_refresh = tokens.get("jwt_refresh")

        request.state.new_tokens = {
            settings.JWT_ACCESS_COOKIE: new_access,
            settings.JWT_REFRESH_COOKIE: new_refresh,
        }

        # Проверяем новый access
        grpc_request = auth_pb2.CheckAccessRequest(jwt_access=new_access)
        res = await auth_grpc_stub.CheckAccess(grpc_request)

        response_body = BaseResponse(
            status=res.meta.status,
            message=res.meta.message,
            detail=utils.parse_grpc_detail(res.meta.detail),
        )

        logger.info(f"Ответ от CheckAccessRequest: {response_body.model_dump()}")

        if response_body.status == "success":
            return response_body.detail.get("payload").get("user_id")

        raise exc
    except Exception as e:
        request.state.clear_cookies = True
        raise


Bearer = Annotated[str, Depends(bearer)]
WalletServiceStub = Annotated[
    wallet_pb2_grpc.WalletServiceStub, Depends(wallet_grpc_client.get_stub)
]
