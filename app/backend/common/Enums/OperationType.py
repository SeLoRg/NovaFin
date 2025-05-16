import enum


class OperationType(enum.Enum):
    CONVERT = "convert"
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
