from decimal import Decimal
from common.Enums import ValuteCode, PaymentWorker
from common.gRpc.wallet_service import wallet_pb2, wallet_pb2_grpc
import grpc
from google.protobuf.json_format import ParseDict, MessageToDict
from wallet_service.Core.logger import logger
from wallet_service.exceptions.catch_errors import catch_errors
from wallet_service.app.services.WalletCore import wallet_core
from wallet_service.Core.async_database_helper import async_database_helper


class WalletServiceServicer(wallet_pb2_grpc.WalletServiceServicer):
    @catch_errors(logger=logger)
    async def CreateWallet(
        self, request: wallet_pb2.CreateWalletRequest, context: grpc.ServicerContext
    ) -> wallet_pb2.WalletResponse:
        """Создание нового кошелька для пользователя"""
        logger.info("-------Создание нового кошелька для пользователя-------")

        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.create_wallet(
                session=session, user_id=request.user_id
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.WalletResponse())

    @catch_errors(logger=logger)
    async def GetBalance(
        self, request: wallet_pb2.GetBalanceRequest, context: grpc.ServicerContext
    ):
        """Получение баланса по кошельку"""
        logger.info("-------Получение баланса по кошельку-------")

        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.get_balance(
                session=session,
                user_id=request.user_id,
                currency=ValuteCode(request.currency) if request.currency else None,
            )

        return ParseDict(service_result, wallet_pb2.BalanceResponse())

    @catch_errors(logger=logger)
    async def Transfer(
        self, request: wallet_pb2.TransferRequest, context: grpc.ServicerContext
    ):
        """Перевод средств между кошельками"""
        logger.info("-------Перевод средств между кошельками-------")

        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.transfer(
                session=session,
                sender_id=int(request.from_user_id),
                recipient_id=int(request.to_user_id),
                amount=request.amount,
                currency=ValuteCode(request.currency),
                idempotency_key=request.idempotency_key,
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.OperationResponse())

    @catch_errors(logger=logger)
    async def Convert(
        self, request: wallet_pb2.ConvertRequest, context: grpc.ServicerContext
    ):
        """Конвертация валюты в кошельке"""
        logger.info("-------Конвертация валюты в кошельке-------")
        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.convert_currency(
                session=session,
                user_id=int(request.user_id),
                amount=Decimal(str(request.amount)),
                from_currency=ValuteCode(request.from_currency),
                to_currency=ValuteCode(request.to_currency),
                idempotency_key=request.idempotency_key,
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.OperationResponse())

    @catch_errors(logger=logger)
    async def CreatePaymentTransaction(
        self,
        request: wallet_pb2.CreatePaymentTransactionRequest,
        context: grpc.ServicerContext,
    ):
        """Создание транзакции на оплату через платежный шлюз"""
        logger.info("-------Создание транзакции на оплату через платежный шлюз-------")

        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.deposit_create_checkout(
                session=session,
                user_id=int(request.user_id),
                amount=request.amount,
                currency=ValuteCode(request.currency),
                getaway=PaymentWorker(request.gateway),
                idempotency_key=request.idempotency_key,
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.PaymentTransactionResponse())

    @catch_errors(logger=logger)
    async def ConnectAccountStripe(
        self,
        request: wallet_pb2.ConnectAccountStripeRequest,
        context: grpc.ServicerContext,
    ):
        """Подключение аккаунта Stripe"""
        logger.info("-------Подключение аккаунта Stripe-------")

        async with async_database_helper.session_factory() as session:
            service_result: dict = await wallet_core.connect_account_stripe(
                session=session,
                user_id=int(request.user_id),
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.PaymentTransactionResponse())

    @catch_errors(logger=logger)
    async def HandleStripePayment(
        self,
        request: wallet_pb2.StripePaymentNotification,
        context: grpc.ServicerContext,
    ):
        """Обработка колбека от Stripe"""
        logger.info("-------Обработка колбека от Stripe-------")

        async with async_database_helper.session_factory() as session:
            json_data = MessageToDict(request, preserving_proto_field_name=True)
            logger.info(f"json_data: {json_data}")
            service_result: dict = await wallet_core.handle_stripe_deposit_webhook(
                session=session, payload=json_data
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.WebhookResponse())

    async def HandleStripePayout(
        self,
        request: wallet_pb2.StripePaymentNotification,
        context: grpc.ServicerContext,
    ):
        """Обработка колбека от Stripe"""
        logger.info("-------Обработка колбека от Stripe-------")

        async with async_database_helper.session_factory() as session:
            json_data = MessageToDict(request, preserving_proto_field_name=True)
            logger.info(f"json_data: {json_data}")
            service_result: dict = await wallet_core.handle_stripe_withdraw_webhook(
                session=session, payload=json_data
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.WebhookResponse())

    @catch_errors(logger=logger)
    async def CreateWithdrawTransaction(
        self,
        request: wallet_pb2.WithdrawRequest,
        context: grpc.ServicerContext,
    ):
        """Списание средств с кошелька"""
        logger.info("-------Создание выплаты-------")

        async with async_database_helper.session_factory() as session:
            json_data = MessageToDict(request, preserving_proto_field_name=True)
            logger.info(f"json_data: {json_data}")
            service_result: dict = await wallet_core.withdraw(
                session=session,
                user_id=int(request.user_id),
                amount=Decimal(str(request.amount)),
                currency=ValuteCode(request.currency),
                gateway=PaymentWorker(request.getaway),
                idempotency_key=request.idempotency_key,
            )
            await session.commit()

        return ParseDict(service_result, wallet_pb2.OperationResponse())
