from uuid import UUID, uuid4
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import Numeric, DateTime, func, ForeignKey, Enum
import datetime
from typing import TYPE_CHECKING, Optional
from common.Models.Base import Base
from common.Enums.OperationType import OperationType
from common.Enums.ValuteCode import ValuteCode
from common.Enums.TransactionStatus import TransactionStatus
from common.Enums.PaymentWorker import PaymentWorker

if TYPE_CHECKING:
    from common.Models.Users import Users
    from common.Models.Wallet import Wallet


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    currency: Mapped[ValuteCode] = mapped_column(Enum(ValuteCode), nullable=True)
    from_currency: Mapped[ValuteCode] = mapped_column(Enum(ValuteCode), nullable=True)
    to_currency: Mapped[ValuteCode] = mapped_column(
        Enum(ValuteCode), nullable=True
    )  # может быть null, если просто пополнение или списание
    amount = mapped_column(Numeric(precision=18, scale=2), nullable=False)
    operation_type: Mapped[OperationType] = mapped_column(
        Enum(OperationType), nullable=False
    )  # например, CONVERT, TRANSFER, DEPOSIT, WITHDRAW
    status: Mapped[TransactionStatus] = mapped_column(  # Добавил статус операции
        default=TransactionStatus.PENDING.value,
        server_default=TransactionStatus.PENDING.value,
    )
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    correlation_id: Mapped[UUID] = mapped_column(nullable=True)
    external_id: Mapped[str] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(nullable=False)
    payment_worker: Mapped[PaymentWorker] = mapped_column(nullable=True)

    # Внешний ключ на FiatWallet
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    to_wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=True)
    from_wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=True)

    # many_to_one
    wallet: Mapped["Wallet"] = relationship(
        foreign_keys=[wallet_id], back_populates="transactions"
    )
    from_wallet: Mapped[Optional["Wallet"]] = relationship(
        foreign_keys=[from_wallet_id]
    )
    to_wallet: Mapped[Optional["Wallet"]] = relationship(foreign_keys=[to_wallet_id])
