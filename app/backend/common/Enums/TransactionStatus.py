from enum import Enum


class TransactionStatus(str, Enum):
    """Статусы транзакций"""

    PENDING = "PENDING"
    PROCESSED = "PROCESSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    CANCELLED = "CANCELLED"
