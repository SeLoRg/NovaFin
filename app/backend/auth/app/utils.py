import json
from typing import Any
import httpx
import bcrypt
import hashlib
import time
import uuid
from datetime import datetime, timezone, timedelta
import grpc
import jwt
from auth.Core.config import settings
from auth.app.crud.redis_sessions import redis_sessions_helper
from auth.app.logger import logger
from common.gRpc.auth import auth_pb2


def get_email_verifi_code(login: str) -> str:
    raw_data = f"{login}_{uuid.uuid4()}"
    verification_code = hashlib.sha256(raw_data.encode()).hexdigest()
    return verification_code


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=8)
    hash_pwd = bcrypt.hashpw(password=password.encode(), salt=salt)
    return hash_pwd.decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_jwt_token(
    live: float,
    **kwargs,
) -> str:
    """
    :param live: время жизни токена в минутах
    """
    payload: dict = {
        **kwargs,
        "iat": datetime.now(tz=timezone.utc).timestamp(),
        "exp": (datetime.now(tz=timezone.utc) + timedelta(minutes=live)).timestamp(),
    }
    private_key = settings.jwt_private_key.read_text()

    return jwt.encode(
        payload=payload,
        key=private_key,
        algorithm=settings.jwt_algorithm,
    )


async def generate_and_store_tokens(user_id: str) -> dict:
    refresh_id = str(uuid.uuid4())
    tokens = {
        "jwt_access": create_jwt_token(
            live=settings.jwt_access_live_m, user_id=user_id
        ),
        "jwt_refresh": create_jwt_token(
            live=settings.jwt_refresh_live_m, refresh_id=refresh_id
        ),
    }
    logger.info(f"Push refresh token in redis...")
    await redis_sessions_helper.add_refresh_token(
        user_id=user_id, refresh_token=refresh_id
    )
    logger.info(f"Token pushed")

    return tokens


def decode_tokens(token: str, verify_exp: bool = True) -> dict:
    public_key = settings.jwt_public_key.read_text()
    return jwt.decode(
        jwt=token,
        key=public_key,
        algorithms=settings.jwt_algorithm,
        options={"verify_exp": verify_exp},
    )


def parse_detail_values_to_json(
    detail: dict[str, str | Any], meta: auth_pb2.BaseResponse
) -> auth_pb2.BaseResponse:
    for k, v in detail.items():
        if not isinstance(v, str):
            meta.detail[k] = json.dumps(v)
            continue

        meta.detail[k] = v

    return meta


def parse_response_pydantic_to_grpc(response_pydantic, response_grpc):
    meta = auth_pb2.BaseResponse(
        status=response_pydantic.status,
        message=response_pydantic.message,
    )

    meta = parse_detail_values_to_json(detail=response_pydantic.detail, meta=meta)

    return response_grpc(meta=meta)


async def get_google_tokens(code: str, client: httpx.AsyncClient) -> str:
    # Обмен кода на токен
    token_resp = await client.post(
        settings.GOOGLE_TOKEN_URL,
        data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise grpc.RpcError("No access token")

    return access_token


async def get_google_user_info(access_token: str, client: httpx.AsyncClient) -> dict:
    userinfo_response = await client.get(
        settings.GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )

    if userinfo_response.status_code != 200:
        raise grpc.RpcError("Failed to fetch user info")

    userinfo = userinfo_response.json()

    return userinfo
