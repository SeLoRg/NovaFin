from pydantic import BaseModel, Field, model_validator
from typing import Literal, Any, Optional, Dict
from common.Enums.OperationType import OperationType
from common.Enums.ValuteCode import ValuteCode


class BaseResponse(BaseModel):
    status: Literal["success", "error"]
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


class WalletTransactionResult(BaseModel):
    status: Literal["success", "error"]
    operation: OperationType = Field(..., description="Тип операции")
    wallet_id: int = Field(
        ..., description="ID основного кошелька пользователя для операции"
    )
    idempotency_key: str = Field(
        description="idempotency key для предотвразений дублей"
    )
    correlation_id: str = Field(description="id операции")
    amount: float

    def to_dict(self):
        return {
            "status": self.status,
            "operation": self.operation.value,
            "wallet_id": self.wallet_id,
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
            "amount": self.amount,
        }


class WalletTransactionRequest(BaseModel):
    operation: OperationType = Field(..., description="Тип операции")
    amount: float = Field(
        ..., gt=0, description="Сумма операции (должна быть больше нуля)"
    )
    idempotency_key: str = Field(
        description="idempotency key для предотвразений дублей"
    )
    correlation_id: str
    retries: int = Field(default=0, description="кол-во попыток обработать сообщение")
    wallet_id: int = Field(
        description="ID основного кошелька пользователя для операции"
    )
    to_currency: Optional[ValuteCode] = Field(
        None, description="Валюта зачисления для конвертации или перевода"
    )

    to_wallet_id: Optional[int] = Field(
        None, description="ID кошелька получателя (для перевода)"
    )

    currency: ValuteCode = Field(
        description="Валюта операции, если она одна (например, при депозите или снятии)",
    )

    def to_dict(self):
        # Возвращает словарь, в котором OperationType преобразован в строку
        return {
            "operation": self.operation.value,
            "amount": self.amount,
            "retries": self.retries,
            "correlation_id": self.correlation_id,
            "wallet_id": self.wallet_id,
            "to_currency": (
                self.to_currency.value if self.to_currency is not None else None
            ),
            "to_wallet_id": (
                self.to_wallet_id if self.to_wallet_id is not None else None
            ),
            "currency": self.currency.value if self.currency is not None else None,
            "idempotency_key": self.idempotency_key,
        }

    @model_validator(mode="after")
    def check_required_fields(self):
        if self.operation == OperationType.CONVERT:
            if not self.to_currency:
                raise ValueError(
                    "Для создания операции CONVERT нужно поле 'to_currency'."
                )
        if self.operation == OperationType.TRANSFER:
            if not self.to_wallet_id:
                raise ValueError(
                    "Для создания операции TRANSFER нужно поле 'to_wallet_id'."
                )

        if not self.correlation_id or not self.idempotency_key:
            raise ValueError(f"Нет correlation_id/idempotency_key")

        return self
