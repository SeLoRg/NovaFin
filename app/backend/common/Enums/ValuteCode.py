from enum import Enum
from common.Enums.WalletAccountType import WalletAccountType


class ValuteCode(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"

    # Крипта
    BTC = "BTC"
    ETH = "ETH"
    USDT = "USDT"

    @property
    def type(self) -> WalletAccountType:
        return (
            WalletAccountType.CRYPTO
            if self.value in {"BTC", "ETH", "USDT"}
            else WalletAccountType.FIAT
        )
