import stripe
from google.protobuf.json_format import MessageToDict
from fastapi import Request, HTTPException

from common.Enums import PaymentWorker, ValuteCode
from common.gRpc.wallet_service import wallet_pb2
from getaway.Core.config import settings
from getaway.app import dependencies
from getaway.app.logger import logger
from getaway.app.wallet_service.schemas import (
    StripeWithdrawRequest,
    PaymentTransactionResponse,
    OperationResponse,
    StripeCallbackData,
)


async def stripe_withdraw(
    request_data: StripeWithdrawRequest,
    wallet_grpc_stub: dependencies.WalletServiceStub,
    user_id: dependencies.Bearer,
) -> OperationResponse:
    """Создание транзакции для платежного шлюза"""
    logger.info(f"--Создание выплаты через шлюз--")

    if request_data.currency != ValuteCode.USD:
        raise ValueError("Stripe поддерживает вывывод средст только на USD карту")

    request_to_grpc = wallet_pb2.WithdrawRequest(
        user_id=user_id,
        currency=ValuteCode.USD.value,
        amount=request_data.amount,
        getaway=PaymentWorker.STRIPE.value,
        idempotency_key=request_data.idempotency_key,
    )
    response_from_grpc = await wallet_grpc_stub.CreateWithdrawTransaction(
        request=request_to_grpc
    )
    result = MessageToDict(response_from_grpc, preserving_proto_field_name=True)
    logger.debug(f"Ответ: {result}")

    return OperationResponse(**result)


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
    logger.debug(f"Ответ: {result}")

    return PaymentTransactionResponse(redirect_url=result.get("redirect_url"))


async def stripe_callback_payout(
    data: StripeCallbackData,
    request: Request,
    wallet_grpc_stub: dependencies.WalletServiceStub,
):
    try:
        logger.info(f"---Callback payout stripe---")
        logger.debug(f"{data.model_dump()}")

        # 1. Верификация подписи
        signature = request.headers.get("stripe-signature")
        if not stripe:
            raise HTTPException(status_code=403, detail="Missing Stripe signature")

        payload = await request.body()

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_PAYOUT_SECRET
            )
        except HTTPException as e:
            logger.error(f"Stripe verification failed: {e.detail}")
            raise

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
            ),
            idempotency_key=data.idempotency_key,
        )
        logger.debug(f"gRPC Request: {grpc_request}")
        # 3. Вызов gRPC сервиса
        grpc_response = await wallet_grpc_stub.HandleStripePayout(grpc_request)

        # 4. Обработка ответа
        if not grpc_response.success:
            raise HTTPException(
                status_code=503,
                detail=grpc_response.message or "Payout processing failed",
            )

        return {"status": "OK", "message": grpc_response.message}

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error processing callback: {str(e)}"
        )


async def stripe_callback_payment(
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

        logger.debug(f"Callback request: {data}")
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
            ),
            idempotency_key=data.idempotency_key,
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
