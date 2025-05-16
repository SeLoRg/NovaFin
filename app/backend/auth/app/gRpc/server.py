import json

import grpc

from common.schemas import BaseResponse
from common.gRpc.auth import auth_pb2, auth_pb2_grpc
from auth.exceptions.catch_errors import catch_errors
from auth.app.logger import logger
from auth.app import services, utils
from auth.Core.database_helper import async_database_helper
from grpc import RpcContext
from auth.Core.redis_client import redis_client


class AuthServiceServicer(auth_pb2_grpc.AuthServiceServicer):
    @catch_errors(logger=logger, response_class=auth_pb2.CheckAccessResponse)
    async def CheckAccess(self, request, context: RpcContext):
        res: BaseResponse = await services.check_access(request.jwt_access)
        response = utils.parse_response_pydantic_to_grpc(
            response_pydantic=res, response_grpc=auth_pb2.CheckAccessResponse
        )

        return response

    @catch_errors(logger=logger, response_class=auth_pb2.GetNewTokensResponse)
    async def GetNewTokens(self, request, context: RpcContext):
        res: BaseResponse = await services.get_new_tokens(
            jwt_access=request.jwt_access, jwt_refresh=request.jwt_refresh
        )

        response = utils.parse_response_pydantic_to_grpc(
            response_pydantic=res, response_grpc=auth_pb2.GetNewTokensResponse
        )

        return response

    @catch_errors(logger=logger, response_class=auth_pb2.LoginResponse)
    async def Login(self, request, context):
        async with async_database_helper.session_factory() as session:
            res: BaseResponse = await services.login(
                email=request.user_email,
                password=request.password,
                session=session,
                redis_cli=redis_client,
            )
            response = utils.parse_response_pydantic_to_grpc(
                response_pydantic=res, response_grpc=auth_pb2.LoginResponse
            )

            return response

    @catch_errors(logger=logger, response_class=auth_pb2.LogoutResponse)
    async def Logout(self, request, context):
        res: BaseResponse = await services.logout(
            jwt_access=request.jwt_access, jwt_refresh=request.jwt_refresh
        )
        response = utils.parse_response_pydantic_to_grpc(
            response_pydantic=res, response_grpc=auth_pb2.LogoutResponse
        )
        return response

    @catch_errors(logger=logger, response_class=auth_pb2.RegistrateResponse)
    async def Registrate(self, request, context):
        async with async_database_helper.session_factory() as session:
            res: BaseResponse = await services.register(
                login=request.login, password=request.password, session=session
            )
            response = utils.parse_response_pydantic_to_grpc(
                response_pydantic=res, response_grpc=auth_pb2.RegistrateResponse
            )

            await session.commit()
            return response

    @catch_errors(logger=logger, response_class=auth_pb2.Verify2faResponse)
    async def Verify_2fa(self, request, context):
        res: BaseResponse = await services.verify_2fa(
            user_id=request.user_id, otp_code=request.opt_code, redis_cli=redis_client
        )
        response = utils.parse_response_pydantic_to_grpc(
            response_pydantic=res, response_grpc=auth_pb2.Verify2faResponse
        )

        return response

    @catch_errors(logger=logger, response_class=auth_pb2.HandleGoogleCallbackResponse)
    async def Handle_google_callback(self, request, context):
        async with async_database_helper.session_factory() as session:
            res: BaseResponse = await services.handle_google_callback(
                session=session, code=request.code, redis_cli=redis_client
            )
            response = utils.parse_response_pydantic_to_grpc(
                response_pydantic=res,
                response_grpc=auth_pb2.HandleGoogleCallbackResponse,
            )
            await session.commit()

            return response

    @catch_errors(logger=logger, response_class=auth_pb2.GetGoogleAuthUrlResponse)
    async def Get_google_auth_url(self, request, context):
        res: BaseResponse = await services.get_google_auth_url()
        response = utils.parse_response_pydantic_to_grpc(
            response_pydantic=res,
            response_grpc=auth_pb2.GetGoogleAuthUrlResponse,
        )

        return response


async def serve():
    server = grpc.aio.server(
        options=[
            (
                "grpc.http2.max_pings_without_data",
                0,
            ),  # бесконечно (разрешить пинги без вызовов)
            (
                "grpc.http2.min_time_between_pings_ms",
                300000,
            ),  # не чаще, чем раз в 15 минут
            ("grpc.keepalive_time_ms", 600000),  # пинг каждые 60 сек
            ("grpc.keepalive_timeout_ms", 20000),  # ждать 20 сек ответа на пинг
            (
                "grpc.keepalive_permit_without_calls",
                True,
            ),  # пинговать можно даже без вызовов
        ]
    )
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)
    server.add_insecure_port("[::]:8001")
    await server.start()
    logger.info("Сервер запущен")
    await server.wait_for_termination()
