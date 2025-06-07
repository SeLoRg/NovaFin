import uuid
from decimal import Decimal
from typing import Optional
import stripe
import json
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from common.Enums import TransactionStatus, OperationType, PaymentWorker
from common.Models import (
    WalletAccount,
    WalletTransaction,
    StripeAccounts,
    Users,
    PaymentProviderBalance,
    Currency,
)
from common.crud.CrudDb import CRUD
from common.Enums.ValuteCode import ValuteCode
from common.Models.Wallet import Wallet
from common.schemas import WalletTransactionRequest

from wallet_service.Core.logger import logger
from wallet_service.Core.async_redis_client import async_redis_client
from wallet_service.Core.config import settings
from wallet_service.Core.async_kafka_client import async_kafka_client


stripe.api_key = settings.STRIPE_PRIVATE_KEY


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
        getaway: PaymentWorker,
        currency: ValuteCode,
        idempotency_key: str,
    ) -> dict:
        """Списание средств"""
        logger.info(f"-----Списание средств-------")
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

        logger.info(f"Создание выплаты в зависимости от выбранного шлюза")
        payout_creaters = {PaymentWorker.STRIPE.value: None}

        logger.info(f"Выплата создана")

        logger.info(f"Создание записи о транзакции в бд со статусом PENDING...")
        wallet_transaction = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=int(user_id),
            currency=currency.value,
            amount=amount,
            operation_type=OperationType.WITHDRAW,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            payment_worker=getaway.value,
            wallet_id=user_wallet_id,
            status=TransactionStatus.PENDING,
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

    async def create_payment_transaction_url(
        self,
        session: AsyncSession,
        user_id: str,
        amount: float,
        idempotency_key: str,
        currency: ValuteCode,
        gateway: PaymentWorker,
    ) -> dict:
        """Создание транзакции для платежного шлюза"""
        logger.info(f"--Создание транзакции для платежного шлюза--")

        logger.info(f"Проверка идемпотентности...")
        if await self._check_idempotency(idempotency_key):
            raise ValueError(
                f"Операция с idempotency_key={idempotency_key} уже обработана"
            )

        logger.info(f"Получение кошелька пользователя id={user_id}...")
        user_wallet_id: int = await self._get_wallet_id(
            session=session, user_id=int(user_id)
        )
        logger.info(f"Кошелек получен")

        logger.info(f"Создание записи о транзакции в бд со статусом PENDING...")
        correlation_id = uuid.uuid4()
        wallet_transaction = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=int(user_id),
            amount=amount,
            operation_type=OperationType.DEPOSIT,
            correlation_id=correlation_id,
            currency=currency,
            idempotency_key=idempotency_key,
            wallet_id=user_wallet_id,
            status=TransactionStatus.PENDING,
        )
        logger.info(f"Запись создана")

        logger.info(
            f"Выбор метода создания в зависимоти от платежного шлюза({gateway.value})..."
        )
        handlers = {f"{PaymentWorker.STRIPE.value}": self._create_payment_stripe}
        redirect_url: str = await handlers[gateway.value](
            amount=amount,
            currency=currency,
            wallet_id=user_wallet_id,
            transaction_id=wallet_transaction.id,
        )

        logger.info(f"Кэширование idempotency_key...")
        await self._cashed_idempotency(idempotency_key=idempotency_key)
        logger.info(f"Кэширование успешно")

        return {"redirect_url": redirect_url}

    async def connect_account_stripe(
        self,
        user_id: str,
        session: AsyncSession,
    ) -> dict:
        logger.info(f"Поиск созданного аккаунта в Stripe")
        stripe_accounts: list[StripeAccounts] = await self.crud.get_by_filter(
            session=session, model=StripeAccounts, user_id=int(user_id)
        )
        if len(stripe_accounts) != 0:
            account_id = stripe_accounts[0].stripe_account_id
            logger.info(f"Аккаунт найден id={account_id}")
        else:
            logger.info(f"Аккаунт не найден\nПоиск пользователя")

            user = await self.crud.get_by_filter(
                session=session, model=Users, id=int(user_id)
            )
            user = user.pop()
            logger.info(f"Пользователь найден")
            logger.info(f"Создание аккаунта для пользователя в stripe")
            account: stripe.Account = stripe.Account.create(
                type="express",
                email=user.login,
                capabilities={"transfers": {"requested": True}},
                settings={
                    "payouts": {"schedule": {"interval": "manual"}}
                },  # ручные выплатЫ
            )
            account_id = account.id
            new_stripe_account = await self.crud.create(
                session=session,
                model=StripeAccounts,
                user_id=int(user_id),
                stripe_account_id=account_id,
            )
            logger.info(f"Аккаунт создан")

        # Ссылка на Stripe‑hosted форму, где пользователь введёт банковские реквизиты
        logger.info(f"Создание ссылкаи на Stripe‑hosted форму")
        link: stripe.AccountLink = stripe.AccountLink.create(
            account=account_id,
            type="account_onboarding",
            refresh_url=f"{settings.NOVAFIN_URL}",
            return_url=f"{settings.NOVAFIN_URL}",
        )
        logger.info(f"Ссылка создана")
        return {"redirect_url": link.url}

    async def stripe_callback_deposit(self, session: AsyncSession, data: dict):
        # Идемпотентность
        logger.info(f"Проверка идемпотентности...")
        idempotency_key = data.get("idempotency_key")
        if await self._check_idempotency(idempotency_key):
            return {"success": True, "message": "Success!"}

        # Транзакция из бд
        logger.info(f"Получение записи о транзакции из бд")
        transaction = await self.crud.get_by_filter(
            session=session,
            model=WalletTransaction,
            id=int(data.get("payment_intent").get("metadata").get("transaction_id")),
        )
        transaction = transaction[0]
        logger.info(f"Запись получена")

        event_type = data.get("event_type")
        if event_type != "payment_intent.succeeded":

            logger.info(f"Кэширование idempotency_key...")
            await self._cashed_idempotency(idempotency_key=idempotency_key)
            logger.info(f"Кэширование успешно")

            return {"success": False, "message": "Failed!"}

        # Тестовый режим
        logger.info(f"Проверка на тестовый режим")
        if not data.get("livemode"):
            if not settings.PAYMENT_TEST_MODE:
                logger.info(f"Ответ от шлюза тестовый")

                logger.info(f"Кэширование idempotency_key...")
                await self._cashed_idempotency(idempotency_key=idempotency_key)
                logger.info(f"Кэширование успешно")

                return {"status": True, "message": "Success!"}

        # Отправка в Kafka
        logger.info(f"Отправка сообщения в топик...")
        message = WalletTransactionRequest(
            operation=OperationType.DEPOSIT,
            amount=float(data.get("payment_intent").get("amount")) / 100,
            currency=ValuteCode(data.get("payment_intent").get("currency").upper()),
            idempotency_key=data.get("idempotency_key"),
            correlation_id=str(transaction.correlation_id),
            wallet_id=int(data.get("payment_intent").get("metadata").get("wallet_id")),
        ).to_dict()

        await async_kafka_client.produce_message(
            topic=settings.WALLET_WORKER_REQUEST_TOPIC,
            message=json.dumps(message),
        )
        logger.info(f"Сообщение отправлено")

        logger.info(f"Обновление статуса транзакции и добавление payment_id")
        transaction.status = TransactionStatus.PROCESSED
        transaction.external_id = data.get("payment_intent").get("payment_id")
        await session.flush()
        logger.info(f"Статус и поле external_id обновлены")

        logger.info(f"Обновление баланса провайдера в бд...")
        await self._update_provider_balance(
            session=session,
            provider=PaymentWorker.STRIPE,
            amount=float(data.get("payment_intent").get("amount")) / 100,
            currency=ValuteCode(data.get("payment_intent").get("currency").upper()),
        )
        logger.info(f"Обновление успешно")

        logger.info(f"Кэширование idempotency_key...")
        await self._cashed_idempotency(idempotency_key=idempotency_key)
        logger.info(f"Кэширование успешно")

        return {"success": True, "message": "Success!"}

    # --- Вспомогательные методы ---

    async def _stripe_payout_creater(
        self, session: AsyncSession, currency: ValuteCode, user_id: int, amount: float
    ):

        stripe_account: list[StripeAccounts] = await self.crud.get_by_filter(
            session=session, model=StripeAccounts, user_id=user_id
        )

        if len(stripe_account) == 0:
            raise ValueError("Connected stripe account not found for this user")

        stripe_account_id = stripe_account[0].stripe_account_id

        account: stripe.Account = stripe.Account.retrieve(
            stripe_account, expand=["requirements"]
        )
        if account.requirements.disabled_reason:
            raise ValueError(
                f"Account not ready: {account.requirements.disabled_reason}"
            )

        transfer: stripe.Transfer = stripe.Transfer.create(
            amount=amount,
            currency=currency.value.lower(),
            destination=stripe_account_id,
            description=f"Manual withdrawal for user {user_id}",
        )

        payout: stripe.Payout = stripe.Payout.create(
            amount=amount,
            currency=currency.value.lower(),
            stripe_account=stripe_account_id,
            method="standard",
        )

        return {
            "transfer_id": transfer.id,
            "payout_id": payout.id,
            "status": payout.status,
        }

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

    @staticmethod
    async def _create_payment_stripe(
        amount: float, currency: ValuteCode, wallet_id: int, transaction_id: int
    ) -> str:
        """Создает платежное намерение в Stripe"""
        logger.info(f"Создание ссылки на платеж через Stripe")
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency.value.lower(),
                        "product_data": {
                            "name": "Пополнение баланса",
                        },
                        "unit_amount": int(amount * 100),  # Переводим в центы/копейки
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=settings.NOVAFIN_URL,
            cancel_url=settings.NOVAFIN_URL,
            metadata={"wallet_id": wallet_id, "transaction_id": transaction_id},
            payment_intent_data={
                "metadata": {
                    "wallet_id": wallet_id,
                    "transaction_id": transaction_id,
                }
            },
        )
        logger.info(f"Ссылка создана")
        return session.url  # URL для редиректа на страницу оплаты Stripe

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

    async def _update_provider_balance(
        self,
        session: AsyncSession,
        provider: PaymentWorker,
        amount: float,
        currency: ValuteCode,
    ):
        logger.info(f"Получение баланса провайдера")
        provider_balance = await self.crud.get_by_filter(
            session=session, model=PaymentProviderBalance, provider=provider
        )
        provider_currencies = {PaymentWorker.STRIPE.value: ValuteCode.USD}

        if len(provider_balance) == 0:
            logger.info(f"Создание баланса для провайдера")
            provider_balance = await self.crud.create(
                session=session,
                model=PaymentProviderBalance,
                provider=provider,
                currency=provider_currencies[provider.value],
                available_amount=0,
            )
        else:
            provider_balance = provider_balance[0]

        logger.info(f"Получение курса {currency} к рублю")
        currency_to_rub = await self.crud.get_by_filter(
            session=session, model=Currency, code=currency.value
        )
        currency_to_rub = currency_to_rub[0]

        if provider == PaymentWorker.STRIPE:
            if currency == provider_balance.currency:
                provider_balance.available_amount += amount
            else:
                logger.info(f"Получение курса {provider_balance.currency} к рублю")
                provider_currency_to_rub = await self.crud.get_by_filter(
                    session=session,
                    model=Currency,
                    code=provider_balance.currency.value,
                )
                provider_currency_to_rub = provider_currency_to_rub[0]

                provider_balance.available_amount = (
                    provider_balance.available_amount
                    + float(
                        (amount * float(currency_to_rub.rate_to_base))
                        / float(provider_currency_to_rub.rate_to_base)
                    )
                )


crud = CRUD()
wallet_core = WalletCore(redis_cli=async_redis_client, crud=crud)
