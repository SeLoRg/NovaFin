from common.Models.Base import Base
from common.Enums.ValuteCode import ValuteCode
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Numeric, DateTime, func
import datetime


class Currency(Base):
    __tablename__ = "currencies"

    code: Mapped[ValuteCode] = mapped_column(
        unique=True, nullable=False
    )  # Например, 'USD', 'EUR'
    rate_to_base = mapped_column(
        Numeric(precision=18, scale=6), nullable=False
    )  # Курс к базовой валюте
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
