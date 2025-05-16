from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from common.crud.CrudDb import CRUD
from common.Models.Wallet import Wallet
from common.Models.WalletAccount import WalletAccount
from common.Enums.ValuteCode import ValuteCode
from common.Models.Currency import Currency
from wallet_worker.Core.logger import logger


class WalletService:
    def __init__(self, crud: CRUD):
        self.crud = crud

    async def create_wallet(self, session: AsyncSession, user_id: int) -> Wallet:
        new_wallet = await self.crud.create(
            session=session, model=Wallet, user_id=user_id
        )
        return new_wallet

    async def delete_wallet(self, session: AsyncSession, wallet_id: int):
        await self.crud.delete_by_id(session=session, model=Wallet, object_id=wallet_id)

    async def get_wallet(self, session: AsyncSession, wallet_id: int) -> Wallet:
        logger.info("Получение Wallet...")
        wallets = await self.crud.get_by_filter(
            session=session, model=Wallet, id=wallet_id
        )
        if not wallets:
            raise ValueError("Кошелек не найден.")

        wallet = wallets[0]
        logger.info(f"Кошелек найден: {wallet.__repr__()}")
        return wallet

    @staticmethod
    async def get_wallet_account(
        session: AsyncSession, wallet: Wallet, currency_code: ValuteCode
    ) -> WalletAccount | None:
        logger.info("Получение счета пользователя...")

        await session.refresh(wallet, attribute_names=["accounts"])

        for account in wallet.accounts:
            if account.currency_code == currency_code:
                logger.info(f"Счет найден: {account.__repr__()}")
                return account

        logger.info(f"Счет не найден")
        return None

    async def _change_balance(
        self,
        session: AsyncSession,
        wallet_id: int,
        currency_code: ValuteCode,
        delta: Decimal,
    ):
        logger.info("---Change Balance---")
        wallet = await self.get_wallet(session, wallet_id)
        account = await self.get_wallet_account(
            session=session, wallet=wallet, currency_code=currency_code
        )

        if account is None:
            if delta < 0:
                raise ValueError("Нельзя списать средства: счёт не существует.")
            logger.info("Создание нового счёта...")
            account = await self.crud.create(
                session=session,
                model=WalletAccount,
                type=currency_code.type,
                wallet_id=wallet_id,
                currency_code=currency_code.value,
                amount=delta,
            )
            logger.info("Счёт создан")
        else:
            new_amount = account.amount + delta
            if new_amount < 0:
                raise ValueError("Недостаточно средств.")
            account = await self.crud.update_by_id(
                session=session,
                model=WalletAccount,
                object_id=account.id,
                amount=new_amount,
            )
            logger.info("Баланс обновлён")

    async def deposit(
        self,
        session: AsyncSession,
        wallet_id: int,
        currency_code: ValuteCode,
        amount: Decimal,
    ):
        logger.info("---Deposit---")
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть больше нуля.")
        await self._change_balance(session, wallet_id, currency_code, amount)

    async def withdraw(
        self,
        session: AsyncSession,
        wallet_id: int,
        currency_code: ValuteCode,
        amount: Decimal,
    ):
        logger.info("---Withdraw---")
        if amount <= 0:
            raise ValueError("Сумма списания должна быть больше нуля.")
        await self._change_balance(session, wallet_id, currency_code, -amount)

    async def transfer(
        self,
        session: AsyncSession,
        from_wallet_id: int,
        to_wallet_id: int,
        currency_code: ValuteCode,
        amount: Decimal,
    ):
        logger.info("---Transfer---")
        if amount <= 0:
            raise ValueError("Сумма перевода должна быть больше нуля.")

        await self._change_balance(session, from_wallet_id, currency_code, -amount)
        await self._change_balance(session, to_wallet_id, currency_code, amount)

    async def convert(
        self,
        session: AsyncSession,
        wallet_id: int,
        from_currency: ValuteCode,
        to_currency: ValuteCode,
        amount: Decimal,
    ):
        logger.info("---Convert---")
        if amount <= 0:
            raise ValueError("Сумма для конвертации должна быть больше нуля.")

        from_rate = (
            await self.crud.get_by_filter(session, Currency, code=from_currency)
        )[0].rate_to_base
        to_rate = (await self.crud.get_by_filter(session, Currency, code=to_currency))[
            0
        ].rate_to_base

        converted_amount = amount * from_rate / to_rate

        await self._change_balance(session, wallet_id, from_currency, -amount)
        await self._change_balance(session, wallet_id, to_currency, converted_amount)


crud = CRUD()
wallet_service = WalletService(crud=crud)
