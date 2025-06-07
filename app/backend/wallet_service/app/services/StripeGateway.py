from __future__ import annotations
from typing import Any, Dict, List, Optional
import stripe

from common.Enums.ValuteCode import ValuteCode
from wallet_service.Core import async_kafka_client, logger
from wallet_service.Core.config import settings


class StripeGateway:
    """All direct calls to the Stripe SDK live here."""

    @staticmethod
    async def create_checkout_session(
        amount: float, currency: ValuteCode, wallet_id: int, tx_id: int
    ) -> str:
        logger.info("Stripe: creating Checkout Session")

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency.value.lower(),
                        "product_data": {"name": "Пополнение баланса"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=settings.NOVAFIN_URL,
            cancel_url=settings.NOVAFIN_URL,
            metadata={"wallet_id": wallet_id, "transaction_id": tx_id},
            payment_intent_data={
                "metadata": {"wallet_id": wallet_id, "transaction_id": tx_id},
            },
        )
        return session.url

    @staticmethod
    async def create_connected_account(email: str) -> str:
        account: stripe.Account = stripe.Account.create(
            type="express",
            email=email,
            capabilities={"transfers": {"requested": True}},
            settings={"payouts": {"schedule": {"interval": "manual"}}},
        )
        return account.id

    @staticmethod
    async def onboarding_link(account_id: str) -> str:
        link: stripe.AccountLink = stripe.AccountLink.create(
            account=account_id,
            type="account_onboarding",
            refresh_url=settings.NOVAFIN_URL,
            return_url=settings.NOVAFIN_URL,
        )
        return link.url

    @staticmethod
    async def verify_account_ready(account_id: str) -> None:
        account: stripe.Account = stripe.Account.retrieve(
            account_id, expand=["requirements"]
        )
        if account.requirements.disabled_reason:
            raise ValueError(
                f"Stripe account not ready: {account.requirements.disabled_reason}"
            )

    @staticmethod
    async def payout(
        amount_minor: int,
        account_id: str,
        currency: ValuteCode,
        wallet_id: int,
        tx_id: int,
    ) -> Dict[str, str]:
        """amount_minor - сумма в центах/копейках"""
        logger.debug(f"Перевод средств на аккаунт: {account_id}")
        transfer = stripe.Transfer.create(
            amount=amount_minor,
            currency=currency.value.lower(),
            destination=account_id,
            description="Wallet withdrawal",
        )
        logger.debug(f"Создание выплаты с аккаунта: {account_id}")
        payout = stripe.Payout.create(
            amount=amount_minor,
            currency=currency.value.lower(),
            stripe_account=account_id,
            method="standard",
            metadata={
                "wallet_id": wallet_id,
                "transaction_id": tx_id,
            },
        )
        return {
            "transfer_id": transfer.id,
            "payout_id": payout.id,
            "status": payout.status,
        }
