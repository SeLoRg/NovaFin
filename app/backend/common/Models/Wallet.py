from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, func
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from .Base import Base

if TYPE_CHECKING:
    from common.Models.WalletTransaction import WalletTransaction
    from common.Models.WalletAccount import WalletAccount
    from common.Models.Users import Users


class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("Users.id"), unique=True
    )  # users с маленькой буквы
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["Users"] = relationship(back_populates="wallet")

    accounts: Mapped[list["WalletAccount"]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan",
        lazy="selectin",  # Для быстрой загрузки вместе с кошельком
    )

    transactions: Mapped[list["WalletTransaction"]] = relationship(
        back_populates="wallet",
        cascade="all, delete-orphan",
        primaryjoin="Wallet.id == WalletTransaction.wallet_id",
        order_by="desc(WalletTransaction.date)",  # Сортировка по умолчанию
    )

    def __repr__(self):
        return f"<Wallet user_id={self.user_id}>"
