import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum
import json
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from common.Enums import TransactionStatus, OperationType
from common.Models import WalletAccount, WalletTransaction
from common.crud.CrudDb import CRUD
from common.Enums.WalletAccountType import WalletAccountType
from common.Enums.ValuteCode import ValuteCode
from common.Models.Wallet import Wallet
from common.schemas import WalletTransactionRequest

from wallet_service.Core.logger import logger
from wallet_service.Core.async_redis_client import async_redis_client
from wallet_service.Core.config import settings
from wallet_service.Core.async_kafka_client import async_kafka_client


# Модели данных (аналоги protobuf-сообщений)
class PaymentGateway(str, Enum):
    STRIPE = "stripe"
    CLOUDPAYMENTS = "cloudpayments"


class WalletCore:
    def __init__(self, redis_cli: Redis, crud: CRUD):
        self.redis = redis_cli  # Redis клиент
        self.crud = crud  # CRUD

    # --- Основные методы ---

    async def create_wallet(self, session: AsyncSession, user_id: str) -> dict:
        """Создание нового кошелька"""

        logger.info(f"Создание кошелька для user_id={user_id}")
        new_wallet = await self.crud.create(
            session=session, model=Wallet, user_id=int(user_id)
        )
        logger.info(f"Кошелек создан")
        return {
            "wallet_id": str(new_wallet.id),
            "created_at": str(new_wallet.created_at),
        }

    async def get_balance(
        self,
        session: AsyncSession,
        user_id: str,
        currency: Optional[ValuteCode] = None,
    ) -> dict:
        """Получение баланса"""
        logger.info(f"Поиск кошелька...")
        wallet: list[Wallet] = await self.crud.get_by_filter(
            session=session, model=Wallet, user_id=int(user_id)
        )

        if len(wallet) == 0:
            raise ValueError(f"Кошелек не найден")

        wallet: Wallet = wallet.pop()
        logger.info(f"Кошелек найден")
        logger.info(f"Получение счетов пользователя...")

        await session.refresh(wallet, attribute_names=["accounts"])

        accounts: list[WalletAccount] = []

        for account in wallet.accounts:
            if currency is None:
                accounts.append(account)
                continue

            if account.currency_code == currency:
                accounts.append(account)

        logger.info(f"Счета получены")
        return {
            "user_id": str(user_id),
            "balances": [account.to_dict() for account in accounts],
        }

    async def transfer(
        self,
        session: AsyncSession,
        from_user_id: str,
        to_user_id: str,
        amount: float,
        currency: ValuteCode,
        idempotency_key: str,
    ) -> dict:
        """Перевод средств"""
        logger.info(f"-----Перевод средств-------")
        logger.info(f"Проверка идемпотентности...")
        if await self._check_idempotency(idempotency_key):
            raise ValueError(
                f"Операция с idempotency_key={idempotency_key} уже обработана"
            )

        logger.info(f"Получение кошелька пользователя id={from_user_id}...")
        from_user_wallet_id: int = await self._get_wallet_id(
            session=session, user_id=int(from_user_id)
        )
        logger.info(f"Кошелек получен")

        logger.info(f"Получение кошелька пользователя id={to_user_id}...")
        to_user_wallet_id: int = await self._get_wallet_id(
            session=session, user_id=int(to_user_id)
        )
        logger.info(f"Кошелек получен")

        correlation_id = str(uuid.uuid4())

        logger.info(
            f"Отправка сообщения для wallet_worker на обработку операции TRANSFER..."
        )
        await self._send_to_kafka(
            operation=OperationType.TRANSFER,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            from_wallet_id=from_user_wallet_id,
            to_wallet_id=to_user_wallet_id,
        )
        logger.info(f"Сообщение отправлено")

        logger.info(f"Создание записи о транзакции в бд со статусом PROCESSED...")
        wallet_transaction = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=int(from_user_id),
            currency=currency.value,
            amount=Decimal(str(amount)),
            operation_type=OperationType.TRANSFER,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            wallet_id=from_user_wallet_id,
            to_wallet_id=to_user_wallet_id,
            from_wallet_id=from_user_wallet_id,
            status=TransactionStatus.PROCESSED,
        )
        logger.info(f"Запись создана")

        logger.info(f"Кэширование idempotency_key...")
        await self._cashed_idempotency(idempotency_key=idempotency_key)
        logger.info(f"Кэширование успешно")

        response = {
            "correlation_id": correlation_id,
            "status": wallet_transaction.status.value,
        }

        return response

    async def convert(
        self,
        session: AsyncSession,
        user_id: str,
        amount: Decimal,
        from_currency: ValuteCode,
        to_currency: ValuteCode,
        idempotency_key: str,
    ) -> dict:
        """Конвертация средств"""
        logger.info(f"-----Конвертация средств-------")
        logger.info(f"Проверка идемпотентности...")
        if await self._check_idempotency(idempotency_key):
            raise ValueError(
                f"Операция с idempotency_key={idempotency_key} уже обработана"
            )

        correlation_id = str(uuid.uuid4())

        logger.info(f"Получение кошелька пользователя id={user_id}...")
        user_wallet_id: int = await self._get_wallet_id(
            session=session, user_id=int(user_id)
        )
        logger.info(f"Кошелек получен")

        logger.info(
            f"Отправка сообщения для wallet_worker на обработку операции CONVERT..."
        )
        message = WalletTransactionRequest(
            operation=OperationType.CONVERT,
            amount=float(amount),
            currency=from_currency,
            to_currency=to_currency,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            wallet_id=user_wallet_id,
        ).to_dict()

        await async_kafka_client.produce_message(
            topic=settings.WALLET_WORKER_REQUEST_TOPIC, message=json.dumps(message)
        )
        logger.info(f"Сообщение отправлено")

        logger.info(f"Создание записи о транзакции в бд со статусом PROCESSED...")
        wallet_transaction = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=int(user_id),
            from_currency=from_currency.value,
            to_currency=to_currency.value,
            amount=amount,
            operation_type=OperationType.CONVERT,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            wallet_id=user_wallet_id,
            status=TransactionStatus.PROCESSED,
        )
        logger.info(f"Запись создана")

        logger.info(f"Кэширование idempotency_key...")
        await self._cashed_idempotency(idempotency_key=idempotency_key)
        logger.info(f"Кэширование успешно")

        response = {
            "correlation_id": correlation_id,
            "status": wallet_transaction.status.value,
        }

        return response

    async def withdraw(
        self,
        session: AsyncSession,
        user_id: str,
        amount: Decimal,
        currency: ValuteCode,
        idempotency_key: str,
    ) -> dict:
        """Списание средств"""
        pass

    async def deposit(
        self,
        session: AsyncSession,
        user_id: str,
        amount: Decimal,
        currency: ValuteCode,
        idempotency_key: str,
    ) -> dict:
        """Пополнение баланса"""
        pass

    async def create_payment_transaction(
        self,
        session: AsyncSession,
        wallet_id: str,
        amount: float,
        currency: ValuteCode,
        gateway: PaymentGateway,
        external_id: str,
    ) -> dict:
        """Создание транзакции для платежного шлюза"""
        transaction_id = str(uuid.uuid4())

        # Логика сохранения транзакции в статусе PENDING
        # await self.db.execute(...)

        return {
            "transaction_id": transaction_id,
            "status": "PENDING",
            "gateway_url": f"https://{gateway}.com/pay/{external_id}",
            "created_at": datetime.utcnow().isoformat(),
        }

    # --- Вспомогательные методы ---

    async def _check_idempotency(self, idempotency_key: str) -> bool:
        """Проверка, была ли уже обработана операция"""
        return await self.redis.exists(
            f"{settings.REDIS_KEY_IDEMPOTENCY}:{idempotency_key}"
        )

    async def _get_wallet_id(self, session: AsyncSession, user_id: int) -> int:
        wallet: list[Wallet] = await self.crud.get_by_filter(
            session=session, model=Wallet, user_id=user_id
        )

        if len(wallet) == 0:
            raise ValueError("Кошелек не найден")

        return wallet[0].id

    async def _cashed_idempotency(self, idempotency_key: str):
        await self.redis.setex(
            name=f"{settings.REDIS_KEY_IDEMPOTENCY}:{idempotency_key}",
            value="",
            time=24 * 3600,
        )

    @staticmethod
    async def _send_to_kafka(
        operation: OperationType,
        amount: float,
        currency: ValuteCode,
        idempotency_key: str,
        correlation_id: str,
        from_wallet_id: int,
        to_wallet_id: int,
    ) -> None:
        """Отправляет задачу в wallet_worker через Kafka"""
        message = WalletTransactionRequest(
            operation=operation,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            wallet_id=from_wallet_id,
            to_wallet_id=to_wallet_id,
        ).to_dict()

        await async_kafka_client.produce_message(
            topic=settings.WALLET_WORKER_REQUEST_TOPIC, message=json.dumps(message)
        )


crud = CRUD()
wallet_core = WalletCore(redis_cli=async_redis_client, crud=crud)
