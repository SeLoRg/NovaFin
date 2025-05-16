"""Change WalletTransaction | TransactionStatus

Revision ID: 0f614e6aa872
Revises: 5ba33d6df4bb
Create Date: 2025-05-10 12:51:52.335449

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f614e6aa872"
down_revision: Union[str, None] = "5ba33d6df4bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1. Сначала создаем новый тип enum с добавленным значением
    op.execute("ALTER TYPE transactionstatus ADD VALUE 'PROCESSED' AFTER 'PENDING'")

    # 2. Обновляем значение по умолчанию для существующих записей (опционально)
    # op.execute("UPDATE wallet_transactions SET status = 'PROCESSED' WHERE status = 'PENDING' AND <ваши_условия>")


def downgrade():
    # Для отката миграции нужно создать новый enum без PROCESSED и обновить все записи
    # Это сложная операция в PostgreSQL, поэтому часто используют временный столбец

    # 1. Создаем временный столбец с старым enum
    op.add_column(
        "wallet_transactions",
        sa.Column(
            "status_temp",
            sa.Enum(
                "PENDING",
                "COMPLETED",
                "FAILED",
                "REVERSED",
                "CANCELLED",
                name="transactionstatus_old",
            ),
            server_default="PENDING",
        ),
    )

    # 2. Копируем данные из старого столбца в новый, преобразуя PROCESSED в что-то другое
    op.execute(
        """
        UPDATE wallet_transactions 
        SET status_temp = 
            CASE 
                WHEN status = 'PROCESSED' THEN 'PENDING' 
                ELSE status::text::transactionstatus_old 
            END
    """
    )

    # 3. Удаляем старый столбец
    op.drop_column("wallet_transactions", "status")

    # 4. Переименовываем временный столбец
    op.alter_column("wallet_transactions", "status_temp", new_column_name="status")

    # 5. Удаляем старый тип enum
    op.execute("DROP TYPE transactionstatus")

    # 6. Переименовываем временный тип обратно
    op.execute("ALTER TYPE transactionstatus_old RENAME TO transactionstatus")
