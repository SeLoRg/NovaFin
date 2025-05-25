from .Base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey


class StripeAccounts(Base):
    __tablename__ = "stripe_accounts"
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"), unique=True)
    stripe_account_id: Mapped[str]
