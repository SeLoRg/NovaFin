from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from common.Enums import ValuteCode, PaymentWorker, TransactionStatus, WalletAccountType
from common.schemas import BaseResponse


class BalanceEntry(BaseModel):
    currency: ValuteCode
    amount: float
    type: WalletAccountType


class CreateWalletRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")


class Wallet(BaseModel):
    wallet_id: str
    created_at: str


class WalletResponse(BaseResponse):
    detail: Wallet


class GetBalanceRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    currency: Optional[ValuteCode] = None


class BalanceResponse(BaseModel):
    user_id: str
    balances: List[BalanceEntry]


class TransferRequest(BaseModel):
    receiver_user_id: str = Field(..., description="ID пользователя-получателя")
    amount: float
    currency: ValuteCode
    idempotency_key: str


class DepositRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    amount: float
    currency: ValuteCode
    idempotency_key: str
    source: Optional[str] = None


class WithdrawRequest(BaseModel):
    user_id: str = Field(..., description="ID пользователя")
    amount: float
    currency: ValuteCode
    idempotency_key: str
    destination: str


class ConvertRequest(BaseModel):
    from_currency: ValuteCode
    to_currency: ValuteCode
    amount: float
    idempotency_key: str


class OperationResponse(BaseModel):
    correlation_id: str
    status: TransactionStatus


class CreatePaymentTransactionRequest(BaseModel):
    amount: float
    currency: ValuteCode
    gateway: PaymentWorker
    idempotency_key: str


class PaymentTransactionResponse(BaseModel):
    redirect_url: str


class StripeCallbackData(BaseModel):
    id: str  # event_id
    type: str  # event_type
    livemode: bool
    data: dict
    request: dict

    @property
    def idempotency_key(self) -> str:
        return self.request.get("idempotency_key", "")

    @property
    def payment_intent_data(self) -> dict:
        return self.data.get("object", {})
