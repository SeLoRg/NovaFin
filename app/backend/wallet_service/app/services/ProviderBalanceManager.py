from __future__ import annotations
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from common.Enums import OperationType, PaymentWorker, TransactionStatus
from common.Enums.ValuteCode import ValuteCode
from common.Models import (
    Currency,
    PaymentProviderBalance,
)
from common.crud.CrudDb import CRUD
from wallet_service.Core import logger


class ProviderBalanceManager:
    """Tracks liquidity per provider / currency."""

    BASE_CURRENCY_MAP = {PaymentWorker.STRIPE: ValuteCode.USD}

    def __init__(self, crud: CRUD):
        self._crud = crud

    async def change_amount(
        self,
        session: AsyncSession,
        provider: PaymentWorker,
        amount: float,
        currency: ValuteCode,
    ) -> None:
        record_list: List[PaymentProviderBalance] = await self._crud.get_by_filter(
            session=session, model=PaymentProviderBalance, provider=provider
        )
        if not record_list and amount >= 0:
            record = await self._crud.create(
                session=session,
                model=PaymentProviderBalance,
                provider=provider,
                currency=self.BASE_CURRENCY_MAP[provider],
                available_amount=0.0,
            )
        else:
            record = record_list[0]

        # Convert → provider currency if neaded
        if currency != record.currency:
            rate_src = await self.get_rate(session, currency)
            rate_dst = await self.get_rate(session, record.currency)
            amount = amount * rate_src / rate_dst

        record.available_amount += amount
        await session.flush()

    async def get_rate(self, session: AsyncSession, code: ValuteCode) -> float:
        row: Currency = (
            await self._crud.get_by_filter(
                session=session, model=Currency, code=code.value
            )
        )[0]
        return float(row.rate_to_base)
