from .Base import Base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import func, DateTime
from common.Enums import PaymentWorker, ValuteCode
import datetime


class PaymentProviderBalance(Base):
    __tablename__ = "payment_provider_balances"

    provider: Mapped[PaymentWorker] = mapped_column(nullable=False)
    currency: Mapped[ValuteCode] = mapped_column(nullable=False)
    available_amount: Mapped[float]
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
