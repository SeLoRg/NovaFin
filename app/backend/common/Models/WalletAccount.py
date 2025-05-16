from sqlalchemy import ForeignKey, UniqueConstraint, Enum, DECIMAL, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from common.Models import Base
from common.Enums.ValuteCode import ValuteCode
from common.Enums.WalletAccountType import WalletAccountType

if TYPE_CHECKING:
    from common.Models.Wallet import Wallet


class WalletAccount(Base):
    """
    Счета пользователей
    """

    __tablename__ = "wallet_accounts"
    __table_args__ = (
        UniqueConstraint(
            "wallet_id", "currency_code", "type", name="uq_wallet_currency_type"
        ),
    )

    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id"), nullable=False)
    currency_code: Mapped[ValuteCode] = mapped_column(Enum(ValuteCode), nullable=False)
    type: Mapped[WalletAccountType] = mapped_column(
        nullable=False
    )  # например: fiat / crypto
    amount = mapped_column(Numeric(precision=18, scale=2), nullable=False, default=0)

    # many_to_many
    wallet: Mapped["Wallet"] = relationship(back_populates="accounts")

    def to_dict(self):
        return {
            "currency": self.currency_code.value,
            "amount": float(self.amount),
            "type": self.type.value,
        }

    def __repr__(self):
        return f"WalletAccount:type={self.type.value} currency_code={self.currency_code.value}, amount={self.amount}"
