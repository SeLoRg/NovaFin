from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import uuid
from google.protobuf.json_format import MessageToDict

from common.gRpc.wallet_service import wallet_pb2_grpc, wallet_pb2
from getaway.app import dependencies
from getaway.app.wallet_service.schemas import *
from getaway.Core.grpc_clients.wallet_grpc_client import wallet_grpc_client
from getaway.app.logger import logger
from getaway.exceptions.catch_errors import catch_errors
from common.Metrics.metrics import func_work_time
from fastapi.responses import RedirectResponse

router = APIRouter()


# Роуты
@router.post("/create", response_model=WalletResponse)
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
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.info(f"Ответ: {result}")

    return BalanceResponse(
        user_id=result.get("user_id"),
        balances=[BalanceEntry(**data) for data in result.get("balances", [])],
    )


@router.post("/transfer", response_model=OperationResponse)
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


@router.post("/deposit", response_model=OperationResponse)
async def deposit_funds(request: DepositRequest):
    """Пополнение кошелька"""
    return OperationResponse(
        operation_id=str(uuid.uuid4()),
        status=TransactionStatus.PROCESSED,
        timestamp=datetime.utcnow(),
    )


@router.post("/withdraw", response_model=OperationResponse)
async def withdraw_funds(request: WithdrawRequest):
    """Списание средств с кошелька"""
    return OperationResponse(
        operation_id=str(uuid.uuid4()),
        status=TransactionStatus.PROCESSED,
        timestamp=datetime.utcnow(),
    )
