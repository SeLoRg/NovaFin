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
    user_id: str = Field(..., description="ID пользователя")
    amount: float
    currency: ValuteCode
    gateway: PaymentWorker
    external_id: str


class PaymentTransactionResponse(BaseModel):
    transaction_id: str
    user_id: str
    status: str = "PENDING"
    gateway_url: Optional[str] = None
    created_at: datetime
