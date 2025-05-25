from google.protobuf.json_format import MessageToDict

from common.Enums import PaymentWorker, ValuteCode
from common.gRpc.wallet_service import wallet_pb2
from getaway.app import dependencies
from getaway.app.logger import logger
from getaway.app.wallet_service.schemas import (
    CreatePayoutTransactionRequest,
    PaymentTransactionResponse,
)


async def create_payout_transaction(
    request_data: CreatePayoutTransactionRequest,
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    """Создание транзакции для платежного шлюза"""
    logger.info(f"--Создание выплаты через шлюз--")

    if request_data.currency != ValuteCode.USD:
        raise ValueError("Stripe поддерживает вывывод средст только на USD карту")

    request_to_grpc = wallet_pb2.CreatePayoutTransactionRequest(
        user_id=user_id,
        currency=ValuteCode.USD.value,
        amount=request_data.amount,
        gateway=PaymentWorker.STRIPE.value,
        idempotency_key=request_data.idempotency_key,
    )
    response_from_grpc = await wallet_grpc_stub.CreatePayoutTransaction(
        request=request_to_grpc
    )
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    return PaymentTransactionResponse(redirect_url=result.get("redirect_url"))


async def stripe_connect_account(
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    """Подключение аккаунта пользователя в Stripe"""
    logger.info(f"--Подключение аккаунта пользователя в Stripe--")
    request_to_grpc = wallet_pb2.ConnectAccountStripeRequest(
        user_id=user_id,
    )
    response_from_grpc = await wallet_grpc_stub.ConnectAccountStripe(
        request=request_to_grpc
    )
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    return PaymentTransactionResponse(redirect_url=result.get("redirect_url"))
