from .Base import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func, DateTime
from typing import TYPE_CHECKING
import datetime
from common.Enums.AuthProvider import AuthProvider

if TYPE_CHECKING:
    from common.Models.Wallet import Wallet


class Users(Base):
    __tablename__ = "Users"
    password: Mapped[str] = mapped_column(nullable=True)
    login: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(nullable=False)
    email_verification_code: Mapped[str] = mapped_column(
        index=True, unique=True, nullable=True
    )
    phone_number: Mapped[str] = mapped_column(nullable=True, default=None)
    two_factor_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    two_factor_secret: Mapped[str] = mapped_column(nullable=True, default=None)
    auth_provider: Mapped[AuthProvider] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # one_to_one
    wallet: Mapped["Wallet"] = relationship(
        "Wallet", back_populates="user", uselist=False
    )
