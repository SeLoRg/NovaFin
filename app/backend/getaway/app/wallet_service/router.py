import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from datetime import datetime
import uuid

from google.protobuf.internal.well_known_types import Timestamp
from google.protobuf.json_format import MessageToDict, ParseDict

from getaway.Core.config import settings
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


@router.post("/callback/stripe", status_code=200)
async def callback_stripe(
    data: StripeCallbackData,
    request: Request,
    wallet_grpc_stub: dependencies.WalletServiceStub,
):
    try:
        logger.info(f"--Callback от Stripe--")

        # 1. Верификация подписи
        signature = request.headers.get("stripe-signature")
        if not stripe:
            raise HTTPException(status_code=403, detail="Missing Stripe signature")

        payload = await request.body()

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )
        except HTTPException as e:
            logger.error(f"Stripe verification failed: {e.detail}")
            raise

        logger.info(f"Callback request: {data}")
        # 2. Подготовка gRPC запроса
        grpc_request = wallet_pb2.StripePaymentNotification(
            event_id=data.id,
            event_type=data.type,
            livemode=data.livemode,
            payment_intent=wallet_pb2.StripePaymentNotification.PaymentIntent(
                id=data.payment_intent_data.get("id", ""),
                amount=data.payment_intent_data.get("amount", 0),
                currency=data.payment_intent_data.get("currency", ""),
                status=data.payment_intent_data.get("status", ""),
                metadata=data.payment_intent_data.get("metadata", {}),
                payment_method=data.payment_intent_data.get("payment_method", ""),
                customer_email=data.payment_intent_data.get("customer_email", ""),
            ),
            idempotency_key=data.idempotency_key,
            webhook_id=f"wh_{data.id}",  # Генерация webhook_id если нужно
        )
        logger.debug(f"gRPC Request: {grpc_request}")
        # 3. Вызов gRPC сервиса
        grpc_response = await wallet_grpc_stub.HandleStripePayment(grpc_request)

        # 4. Обработка ответа
        if not grpc_response.success:
            raise HTTPException(
                status_code=503,
                detail=grpc_response.message or "Payment processing failed",
            )

        return {"status": "OK", "message": grpc_response.message}

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error processing callback: {str(e)}"
        )


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
