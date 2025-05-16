import random
from urllib.parse import urlencode
import httpx
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from common.Models import Users
from common.Enums.AuthProvider import AuthProvider
from common.schemas import BaseResponse
from auth.app.crud import users_crud
from auth.app.crud.redis_sessions import redis_sessions_helper
from auth.app import utils
from celery_workers.notifications import tasks
from auth.app.logger import logger
from auth.exceptions.exceptions import UserAlreadyExists, WeakPassword
from auth.Core.config import settings
from common.Enums.AuthProvider import AuthProvider


async def register(login: str, password: str, session: AsyncSession) -> BaseResponse:
    logger.info(f"Проверка на существование пользователя с login={login} в системе...")
    check_user: list[Users] = await users_crud.get_users_by_filter(
        session=session, login=login
    )
    if len(check_user) != 0:
        raise UserAlreadyExists(f"User with login {login} already exist")
    logger.info(f"Пользователь не найден")
    hash_pwd: str = utils.hash_password(password)
    email_verification_code: str = utils.get_email_verifi_code(login)

    new_user_data = {
        "login": login,
        "password": hash_pwd,
        "auth_provider": AuthProvider.local,
        "is_active": False,
        "two_factor_enabled": False,
        "email_verification_code": email_verification_code,
    }

    logger.info(f"Создание пользователя {new_user_data}...")
    new_user: Users = await users_crud.create_user(session=session, **new_user_data)
    logger.info(f"Пользователь создан")
    logger.info(f"Отправка на почту с просьбой подтвердить пароль...")
    tasks.send_verification_email.delay(
        email=login, verification_code=email_verification_code
    )
    logger.info(f"Сообщение отправлено")
    return BaseResponse(
        status="success", message="Registration successful! Please verify your email."
    )


async def login(
    email: str, password, session: AsyncSession, redis_cli: Redis
) -> BaseResponse:
    logger.info(f"Try find user with email={email}...")
    user: list[Users] = await users_crud.get_users_by_filter(
        session=session, login=email
    )

    if len(user) != 1:
        raise Exception(f"User not found!")

    logger.info(f"User found")
    logger.info(f"Check inter password...")

    hash_pwd_user: str = user[0].password

    if not utils.verify_password(
        plain_password=password, hashed_password=hash_pwd_user
    ):
        raise WeakPassword("Invalid email or password")

    logger.info(f"The passwords match")
    logger.info(f"Check 2FA...")

    if user[0].two_factor_enabled:
        logger.info("2FA enabled")

        opt = f"{random.randint(100000, 999999):06}"
        user_id = str(user[0].id)
        logger.info(f"Add opt code and attempts in redis...")

        await redis_cli.set(f"{settings.REDIS_KEY_OPT}:{user_id}", opt, ex=300)
        await redis_cli.set(f"{settings.REDIS_KEY_OPT}:{user_id}:attempts", 0, ex=300)

        logger.info(f"Add in redis success")
        logger.info(f"Sending email with code {opt} to {user[0].login}...")
        tasks.send_sms_verify_code.delay(email=user[0].login, opt_code=opt)
        logger.info(f"Email send successfully")

        return BaseResponse(
            status="success",
            message="Enter the verification code sent to your phone.",
            detail={"2FA": True, "user_id": user_id},
        )

    logger.info(f"2FA disabled")
    logger.info(f"Create tokens...")
    user_id = str(user[0].id)
    tokens: dict = await utils.generate_and_store_tokens(user_id=user_id)
    logger.info(f"Tokens created")

    return BaseResponse(
        status="success",
        message="User login successfully!",
        detail={"tokens": tokens},
    )


async def logout(jwt_access: str, jwt_refresh: str) -> BaseResponse:
    logger.info(f"Decoding tokens...")
    access_payload: dict = utils.decode_tokens(jwt_access)
    refresh_payload: dict = utils.decode_tokens(jwt_refresh)
    logger.info(f"Decode success!")
    logger.info(f"Deleting session...")
    await redis_sessions_helper.remove_token(
        user_id=access_payload.get("user_id"),
        refresh_token=refresh_payload.get("refresh_id"),
    )
    logger.info(f"Delete success!")
    return BaseResponse(status="success", message="User logout success.")


async def check_access(jwt_access: str) -> BaseResponse:
    logger.info(f"Decoding jwt access...")
    access_payload: dict = utils.decode_tokens(jwt_access)
    logger.info(f"Decode success!")
    return BaseResponse(
        status="success",
        message="Access is allowed",
        detail={"payload": access_payload},
    )


async def get_new_tokens(jwt_access: str, jwt_refresh: str) -> BaseResponse:
    logger.info(f"Decoding jwt refresh and access...")
    access_payload: dict = utils.decode_tokens(jwt_access, verify_exp=False)
    refresh_payload: dict = utils.decode_tokens(jwt_refresh)
    logger.info(f"Decode success!")

    logger.info(f"Getting user sessions...")
    user_sessions: list[str] = await redis_sessions_helper.get_refresh_tokens(
        user_id=access_payload.get("user_id")
    )
    logger.info(f"sessions:{user_sessions}")
    logger.info(f"Success!")

    if refresh_payload.get("refresh_id").encode() not in user_sessions:
        raise Exception(f"User session not founded.")

    logger.info(f"Remove refresh_id in user sessions...")
    await redis_sessions_helper.remove_token(
        user_id=access_payload.get("user_id"),
        refresh_token=refresh_payload.get("refresh_id"),
    )
    logger.info(f"Success!")
    logger.info(f"Getting new pair of tokens...")
    new_tokens: dict = await utils.generate_and_store_tokens(
        user_id=access_payload.get("user_id")
    )
    logger.info(f"Success!")

    return BaseResponse(
        status="success",
        message="Tokens updated",
        detail={"tokens": new_tokens, "user_id": access_payload.get("user_id")},
    )


async def verify_2fa(user_id: str, otp_code: str, redis_cli: Redis) -> BaseResponse:
    opt = await redis_cli.get(f"2fa:{user_id}")

    if not opt or opt.decode() != otp_code:
        raise Exception("Invalid verification code")

    await redis_cli.delete(f"2fa:{user_id}")
    await redis_cli.delete(f"2fa:{user_id}:attempts")

    tokens = await utils.generate_and_store_tokens(user_id)

    return BaseResponse(
        status="success",
        message="Verification successful",
        detail={"tokens": tokens},
    )


async def get_google_auth_url() -> BaseResponse:
    query = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return BaseResponse(
        status="success",
        message="Redirect url created",
        detail={
            "redirect_url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}"
        },
    )


async def handle_google_callback(
    session: AsyncSession, code: str, redis_cli: Redis
) -> BaseResponse:
    async with httpx.AsyncClient() as client:

        # 1. Получить access_token
        logger.info(f"Получение access_token от google")
        token: str = await utils.get_google_tokens(code=code, client=client)
        logger.info(f"access_token_google: {token}")

        # 2. Получить userinfo
        logger.info(f"Получение userinfo от google")
        user_info: dict = await utils.get_google_user_info(
            access_token=token, client=client
        )
        email = user_info["email"]
        logger.info(f"userinfo: {user_info}")

        # 3. Проверить есть ли пользователь
        logger.info(f"Проверка на существование пользователя")
        user = await users_crud.get_users_by_filter(session=session, login=email)
        if len(user) == 0:
            logger.info(f"Пользователь не найден")
            user = await users_crud.create_user(
                session=session,
                login=email,
                auth_provider=AuthProvider.google,
                is_active=True,
            )

        else:
            user = user[0]

        # 4. Сгенерировать токены и сохранить refresh в redis
        logger.info(f"Генерация токенов")
        tokens = await utils.generate_and_store_tokens(str(user.id))
        logger.info(f"Токены: {tokens}")

        # 5. Отдать токены и редирект ссылку
        response = BaseResponse(
            status="success",
            message="User login grom google success!",
            detail={"tokens": tokens, "redirect_url": None},
        )
        return response
