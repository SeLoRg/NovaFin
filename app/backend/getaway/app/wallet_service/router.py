import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from google.protobuf.json_format import MessageToDict, ParseDict

from getaway.Core.config import settings
from common.gRpc.wallet_service import wallet_pb2_grpc, wallet_pb2
from getaway.app import dependencies
from getaway.app.wallet_service import services
from getaway.app.wallet_service.schemas import *
from getaway.Core.grpc_clients.wallet_grpc_client import wallet_grpc_client
from getaway.app.logger import logger
from getaway.exceptions.catch_errors import catch_errors
from common.Metrics.metrics import func_work_time
from fastapi.responses import RedirectResponse

router = APIRouter()


# Роуты
@router.post("/create", response_model=WalletResponse)
@catch_errors(logger=logger)
async def create_wallet(
    user_id: str = Depends(dependencies.bearer),
    wallet_grpc_stub: wallet_pb2_grpc.WalletServiceStub | None = Depends(
        wallet_grpc_client.get_stub
    ),
):
    """Создание нового кошелька"""

    logger.info(f"--Запрос на создание кошелька--")
    request_to_grpc = wallet_pb2.CreateWalletRequest(user_id=user_id)
    response_from_grpc = await wallet_grpc_stub.CreateWallet(request=request_to_grpc)
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    return WalletResponse(
        status="success", message="Кошелек создан", detail=Wallet(**result)
    )


@router.get("/balance", response_model=BalanceResponse)
@catch_errors(logger=logger)
@func_work_time(logger=logger)
async def get_balance(
    currency: Optional[ValuteCode] = None,
    user_id: str = Depends(dependencies.bearer),
    wallet_grpc_stub: wallet_pb2_grpc.WalletServiceStub | None = Depends(
        wallet_grpc_client.get_stub
    ),
):
    """Получение баланса кошелька"""

    logger.info(f"--Запрос на получение счетов пользователя--")
    request_to_grpc = wallet_pb2.GetBalanceRequest(user_id=user_id)

    if currency is not None and currency.value:
        request_to_grpc.currency = currency.value

    response_from_grpc = await wallet_grpc_stub.GetBalance(request=request_to_grpc)
    result = MessageToDict(
        response_from_grpc,
        preserving_proto_field_name=True,
    )
    logger.debug(f"Ответ: {result}")

    return BalanceResponse(
        user_id=result.get("user_id"),
        balances=[BalanceEntry(**data) for data in result.get("balances", [])],
    )


@router.post("/transfer", response_model=OperationResponse)
@catch_errors(logger=logger)
async def transfer_funds(
    request_data: TransferRequest,
    user_id: str = Depends(dependencies.bearer),
    wallet_grpc_stub: wallet_pb2_grpc.WalletServiceStub = Depends(
        wallet_grpc_client.get_stub
    ),
):
    """Перевод средств между кошельками"""

    logger.info(f"--Запрос на Перевод средств между кошельками--")
    request_to_grpc = wallet_pb2.TransferRequest(
        from_user_id=user_id,
        to_user_id=request_data.receiver_user_id,
        amount=request_data.amount,
        currency=request_data.currency.value,
        idempotency_key=request_data.idempotency_key,
    )
    response_from_grpc = await wallet_grpc_stub.Transfer(request=request_to_grpc)
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    # Здесь будет логика перевода
    return OperationResponse(
        correlation_id=result.get("correlation_id"),
        status=TransactionStatus(result.get("status")),
    )


@router.post("/convert", response_model=OperationResponse)
@catch_errors(logger=logger)
async def convert_currency(
    request_data: ConvertRequest,
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    """Конвертация валюты"""
    logger.info(f"--Запрос на Конвертацию средств между кошельками--")
    request_to_grpc = wallet_pb2.ConvertRequest(
        user_id=user_id,
        to_currency=request_data.to_currency.value,
        from_currency=request_data.from_currency.value,
        amount=request_data.amount,
        idempotency_key=request_data.idempotency_key,
    )
    response_from_grpc = await wallet_grpc_stub.Convert(request=request_to_grpc)
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    # Здесь будет логика перевода
    return OperationResponse(
        correlation_id=result.get("correlation_id"),
        status=TransactionStatus(result.get("status")),
    )


@router.post("/payment-transaction", response_model=PaymentTransactionResponse)
@catch_errors(logger=logger)
async def create_payment_transaction(
    request_data: CreatePaymentTransactionRequest,
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    """Создание транзакции для платежного шлюза"""
    logger.info(f"--Создание транзакции для платежного шлюза--")
    request_to_grpc = wallet_pb2.CreatePaymentTransactionRequest(
        user_id=user_id,
        currency=request_data.currency.value,
        amount=request_data.amount,
        gateway=request_data.gateway.value,
        idempotency_key=request_data.idempotency_key,
    )
    response_from_grpc = await wallet_grpc_stub.CreatePaymentTransaction(
        request=request_to_grpc
    )
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    return PaymentTransactionResponse(redirect_url=result.get("redirect_url"))


@router.post("/stripe/withdraw", response_model=OperationResponse)
@catch_errors(logger=logger)
async def stripe_withdraw(
    request_data: StripeWithdrawRequest,
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    return await services.stripe_withdraw(
        request_data=request_data, wallet_grpc_stub=wallet_grpc_stub, user_id=user_id
    )


@router.get("/stripe/connect-account", response_model=PaymentTransactionResponse)
@catch_errors(logger=logger)
async def stripe_connect_account(
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
):
    return await services.stripe_connect_account(
        wallet_grpc_stub=wallet_grpc_stub, user_id=user_id
    )


@router.post("/stripe/callback/payment", status_code=200)
@catch_errors(logger=logger)
async def stripe_callback_payment(
    data: StripeCallbackData,
    request: Request,
    wallet_grpc_stub: dependencies.WalletServiceStub,
):
    return await services.stripe_callback_payment(
        data=data, request=request, wallet_grpc_stub=wallet_grpc_stub
    )


@router.post("/stripe/callback/payout", status_code=200)
@catch_errors(logger=logger)
async def stripe_callback_payment(
    data: StripeCallbackData,
    request: Request,
    wallet_grpc_stub: dependencies.WalletServiceStub,
):
    return await services.stripe_callback_payout(
        data=data, request=request, wallet_grpc_stub=wallet_grpc_stub
    )
