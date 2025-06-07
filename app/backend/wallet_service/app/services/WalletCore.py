from __future__ import annotations
import json
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

import sqlalchemy.exc
import stripe
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from common.Enums import OperationType, PaymentWorker, TransactionStatus
from common.Enums.ValuteCode import ValuteCode
from common.Models import (
    StripeAccounts,
    Wallet,
    WalletTransaction,
    WalletAccount,
    Users,
    PaymentProviderBalance,
)
from common.crud.CrudDb import CRUD
from common.schemas import WalletTransactionRequest

from wallet_service.Core import async_kafka_client, logger, settings, async_redis_client
from wallet_service.app.services.IdempotencyCache import IdempotencyCache
from wallet_service.app.services.ProviderBalanceManager import ProviderBalanceManager
from wallet_service.app.services.StripeGateway import StripeGateway
from wallet_service.exceptions.exceptions import NoWallet, IdempDone, NoStripeAccount

stripe.api_key = settings.STRIPE_PRIVATE_KEY


class KafkaProducer:
    """Kafka facade to keep WalletCore unaware of implementation details."""

    @staticmethod
    async def send(topic: str, payload: Dict[str, Any]) -> None:
        await async_kafka_client.produce_message(
            topic=topic, message=json.dumps(payload)
        )


class WalletCore:
    """Thin orchestration layer that wires helpers together."""

    def __init__(self, crud: CRUD, redis_cli: Redis):
        self.crud = crud
        self.idemp = IdempotencyCache(redis_cli)
        self.kafka = KafkaProducer()
        self.balances = ProviderBalanceManager(crud)
        self.stripe = StripeGateway()

    # ───────────── Wallet helpers ──────────────

    async def _wallet_id(self, session: AsyncSession, user_id: int) -> int:
        wallets: List[Wallet] = await self.crud.get_by_filter(
            session=session, model=Wallet, user_id=user_id
        )
        if not wallets:
            raise NoWallet("Кошелек не найден")
        return wallets[0].id

    # ───────────── Public API ──────────────

    async def create_wallet(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Создание нового кошелька"""
        try:
            wallet = await self.crud.create(
                session=session, model=Wallet, user_id=int(user_id)
            )
            return {"wallet_id": str(wallet.id), "created_at": str(wallet.created_at)}
        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(f"Ошибка при создании кошелька: {str(e)}")
            raise

    async def get_balance(
        self, session: AsyncSession, user_id: int, currency: Optional[ValuteCode] = None
    ) -> Dict[str, Any]:
        try:
            wallet = (
                await self.crud.get_by_filter(
                    session=session, model=Wallet, user_id=int(user_id)
                )
            )[0]
        except Exception as e:
            raise NoWallet("Кошелек не найден")

        await session.refresh(wallet, attribute_names=["accounts"])
        accounts = [
            acc for acc in wallet.accounts if currency in (None, acc.currency_code)
        ]
        return {
            "user_id": user_id,
            "balances": [acc.to_dict() for acc in accounts],
        }

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
            account_id = await self.stripe.create_connected_account(user.login)
            new_stripe_account = await self.crud.create(
                session=session,
                model=StripeAccounts,
                user_id=int(user_id),
                stripe_account_id=account_id,
            )
            logger.info(f"Аккаунт создан")

        # Ссылка на Stripe‑hosted форму, где пользователь введёт банковские реквизиты
        logger.info(f"Создание ссылки на Stripe‑hosted форму")
        link = await self.stripe.onboarding_link(account_id)
        logger.info(f"Ссылка создана")
        return {"redirect_url": link}

    async def deposit_create_checkout(
        self,
        session: AsyncSession,
        user_id: int,
        amount: float,
        currency: ValuteCode,
        getaway: PaymentWorker,
        idempotency_key: str,
    ) -> Dict[str, str]:
        if await self.idemp.exists(idempotency_key):
            logger.info(f"Операция уже обработана")
            raise IdempDone("Идемпотентная операция уже была обработана")
        try:

            wallet_id = await self._wallet_id(session, user_id)
            tx = await self.crud.create(
                session=session,
                model=WalletTransaction,
                user_id=user_id,
                amount=Decimal(str(amount)),
                currency=currency.value,
                operation_type=OperationType.DEPOSIT,
                status=TransactionStatus.PENDING,
                idempotency_key=idempotency_key,
                wallet_id=wallet_id,
                correlation_id=str(uuid.uuid4()),
            )
            deposit_link_creators = {
                PaymentWorker.STRIPE.value: self.stripe.create_checkout_session
            }
            url = await deposit_link_creators[getaway.value](
                amount, currency, wallet_id, tx.id
            )
            await self.idemp.remember(idempotency_key)
            return {"redirect_url": url}
        except Exception as e:
            logger.error(f"Ошибка при создании ссылки на выплату: {str(e)}")
            raise

    async def handle_stripe_deposit_webhook(
        self, session: AsyncSession, payload: dict
    ) -> dict:
        idemp_key = payload.get("idempotency_key")
        if await self.idemp.exists(idemp_key):
            return {"success": True, "message": "Operation is already done"}
        try:
            pi = payload["payment_intent"]
            tx_id = int(pi["metadata"]["transaction_id"])
            tx: WalletTransaction = (
                await self.crud.get_by_filter(
                    session=session, model=WalletTransaction, id=tx_id
                )
            )[0]
            amount = Decimal(pi["amount"]) / 100
            currency = ValuteCode(pi["currency"].upper())

            logger.debug(f"Обновление баланса провайдера")
            await self.balances.change_amount(
                session, PaymentWorker.STRIPE, float(amount), currency
            )

            worker_pl = WalletTransactionRequest(
                operation=OperationType.DEPOSIT,
                amount=float(amount),
                currency=ValuteCode(currency),
                idempotency_key=idemp_key,
                correlation_id=str(tx.correlation_id),
                wallet_id=int(pi["metadata"]["wallet_id"]),
            ).to_dict()

            await self.kafka.send(
                topic=settings.WALLET_WORKER_REQUEST_TOPIC, payload=worker_pl
            )

            tx.status = TransactionStatus.PROCESSED
            tx.external_id = pi["id"]
            await session.flush()
            await self.idemp.remember(idemp_key)
            return {"success": True, "message": "Callback processed successfully!"}
        except Exception as e:
            logger.error(f"Ошибка при обработке колбека от Stripe: {str(e)}")
            raise

    async def handle_stripe_withdraw_webhook(
        self, session: AsyncSession, payload: dict
    ) -> dict:
        idemp_key = payload.get("idempotency_key")
        if await self.idemp.exists(idemp_key):
            return {"success": True, "message": "Operation is already done"}
        try:
            pi = payload["payment_intent"]
            tx_id = int(pi["metadata"]["transaction_id"])
            tx: WalletTransaction = (
                await self.crud.get_by_filter(
                    session=session, model=WalletTransaction, id=tx_id
                )
            )[0]
            amount = Decimal(pi["amount"]) / 100
            currency = ValuteCode(pi["currency"].upper())

            logger.debug(f"Обновление баланса провайдера")
            await self.balances.change_amount(
                session, PaymentWorker.STRIPE, -float(amount), currency
            )

            worker_pl = WalletTransactionRequest(
                operation=OperationType.WITHDRAW,
                amount=float(amount),
                currency=ValuteCode(currency),
                idempotency_key=idemp_key,
                correlation_id=str(tx.correlation_id),
                wallet_id=int(pi["metadata"]["wallet_id"]),
            ).to_dict()

            await self.kafka.send(
                topic=settings.WALLET_WORKER_REQUEST_TOPIC, payload=worker_pl
            )

            tx.status = TransactionStatus.PROCESSED
            tx.external_id = pi["id"]
            await session.flush()
            await self.idemp.remember(idemp_key)
            return {"success": True, "message": "Callback processed successfully!"}
        except Exception as e:
            logger.error(f"Ошибка при обработке колбека от Stripe: {str(e)}")
            raise

    async def withdraw(
        self,
        session: AsyncSession,
        user_id: int,
        amount: Decimal,
        currency: ValuteCode,
        gateway: PaymentWorker,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        if await self.idemp.exists(idempotency_key):
            raise ValueError("Duplicate operation")
        wallet_id = await self._wallet_id(session, user_id)

        res = await self.get_balance(
            session=session, user_id=user_id, currency=currency
        )
        balance = res["balances"]
        balance_exp = ValueError("Недостаточно средств на балансе пользователя")
        if len(balance) == 0:
            raise balance_exp

        if float(balance[0]["amount"]) < float(amount):
            raise balance_exp

        tx = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=user_id,
            amount=amount,
            currency=currency.value,
            operation_type=OperationType.WITHDRAW,
            status=TransactionStatus.PENDING,
            idempotency_key=idempotency_key,
            wallet_id=wallet_id,
            correlation_id=str(uuid.uuid4()),
            payment_worker=gateway,
        )

        pb: List[PaymentProviderBalance] = await self.crud.get_by_filter(
            session=session, model=PaymentProviderBalance, provider=gateway
        )

        if len(pb) == 0:
            raise ValueError("Недостаточно средств на счету провайдера")

        if float(pb[0].available_amount) < float(amount):
            raise ValueError("Недостаточно средств на счету провайдера")

        if gateway == PaymentWorker.STRIPE:
            sa: List[StripeAccounts] = await self.crud.get_by_filter(
                session=session, model=StripeAccounts, user_id=user_id
            )
            if not sa:
                raise NoStripeAccount("Stripe account not linked")
            account_id = sa[0].stripe_account_id
            await StripeGateway.verify_account_ready(account_id)
            res = await StripeGateway.payout(
                int(amount * 100),
                account_id,
                currency,
                wallet_id=wallet_id,
                tx_id=tx.id,
            )
        else:
            raise NotImplementedError(f"Gateway by {gateway.value} not supported yet")

        tx.status = TransactionStatus.PENDING
        tx.external_id = res["payout_id"]
        await session.flush()
        await self.idemp.remember(idempotency_key)
        return {"correlation_id": str(tx.correlation_id), "status": tx.status.value}

    async def convert_currency(
        self,
        session: AsyncSession,
        user_id: int,
        from_currency: ValuteCode,
        to_currency: ValuteCode,
        amount: Decimal,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Конвертация средств"""
        if await self.idemp.exists(idempotency_key):
            raise ValueError("Duplicate operation")

        correlation_id = str(uuid.uuid4())

        logger.info(f"Получение кошелька пользователя id={user_id}...")
        wallet_id = await self._wallet_id(session, user_id)
        logger.info(f"Кошелек получен")

        logger.info(
            f"Отправка сообщения для wallet_worker на обработку операции CONVERT..."
        )

        message = WalletTransactionRequest(
            operation=OperationType.CONVERT,
            amount=amount,
            currency=from_currency,
            to_currency=to_currency,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            wallet_id=wallet_id,
        ).to_dict()

        await self.kafka.send(
            topic=settings.WALLET_WORKER_REQUEST_TOPIC, payload=message
        )
        logger.info(f"Сообщение отправлено")

        logger.info(f"Создание записи о транзакции в бд со статусом PROCESSED...")
        tx = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=user_id,
            amount=amount,
            currency=from_currency.value,
            operation_type=OperationType.CONVERT,
            status=TransactionStatus.PROCESSED,
            idempotency_key=idempotency_key,
            wallet_id=wallet_id,
            correlation_id=correlation_id,
        )
        logger.info(f"Запись создана")

        logger.info(f"Кэширование idempotency_key...")
        await self.idemp.remember(key=idempotency_key)
        logger.info(f"Кэширование успешно")

        response = {
            "correlation_id": correlation_id,
            "status": tx.status.value,
        }

        return response

    async def transfer(
        self,
        session: AsyncSession,
        sender_id: int,
        recipient_id: int,
        amount: Decimal,
        currency: ValuteCode,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        if await self.idemp.exists(idempotency_key):
            raise ValueError("Duplicate operation")

        logger.info(f"Получение кошелька пользователя id={sender_id}...")
        from_user_wallet_id: int = await self._wallet_id(
            session=session, user_id=int(sender_id)
        )
        logger.info(f"Кошелек получен")

        logger.info(f"Получение кошелька пользователя id={recipient_id}...")
        to_user_wallet_id: int = await self._wallet_id(
            session=session, user_id=int(recipient_id)
        )
        logger.info(f"Кошелек получен")

        correlation_id = str(uuid.uuid4())

        logger.info(
            f"Отправка сообщения для wallet_worker на обработку операции TRANSFER..."
        )
        message = WalletTransactionRequest(
            operation=OperationType.TRANSFER,
            amount=amount,
            currency=currency,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            wallet_id=from_user_wallet_id,
            to_wallet_id=to_user_wallet_id,
        ).to_dict()

        await self.kafka.send(
            topic=settings.WALLET_WORKER_REQUEST_TOPIC, payload=message
        )
        logger.info(f"Сообщение отправлено")

        logger.info(f"Создание записи о транзакции в бд со статусом PROCESSED...")
        wallet_transaction = await self.crud.create(
            session=session,
            model=WalletTransaction,
            user_id=sender_id,
            amount=amount,
            currency=currency.value,
            operation_type=OperationType.TRANSFER,
            status=TransactionStatus.PROCESSED,
            idempotency_key=idempotency_key,
            wallet_id=from_user_wallet_id,
            correlation_id=correlation_id,
        )
        logger.info(f"Запись создана")

        logger.info(f"Кэширование idempotency_key...")
        await self.idemp.remember(key=idempotency_key)
        logger.info(f"Кэширование успешно")

        response = {
            "correlation_id": correlation_id,
            "status": wallet_transaction.status.value,
        }

        return response


# ─────────────────────────── Init singleton  ────────────────────────────

crud = CRUD()
wallet_core = WalletCore(crud=crud, redis_cli=async_redis_client)  # type: ignore
