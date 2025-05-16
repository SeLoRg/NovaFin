"""Update enum ValuteCode

Revision ID: 00e5147f7e6e
Revises: 0f614e6aa872
Create Date: 2025-05-14 18:38:29.684726

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "00e5147f7e6e"
down_revision: Union[str, None] = "0f614e6aa872"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE valutecode ADD VALUE 'BTC'")
    op.execute("ALTER TYPE valutecode ADD VALUE 'ETH'")
    op.execute("ALTER TYPE valutecode ADD VALUE 'USDT'")


def downgrade() -> None:
    op.execute("ALTER TYPE valutecode RENAME TO valutecode_old")

    # Создаем новый enum без криптовалют
    new_valutecode = postgresql.ENUM("RUB", "USD", "EUR", name="valutecode")
    new_valutecode.create(op.get_bind())

    # Применяем изменения к таблицам
    op.execute(
        """
           ALTER TABLE wallet_accounts 
           ALTER COLUMN currency_code TYPE valutecode 
           USING currency_code::text::valutecode
       """
    )

    # Удаляем старый enum
    op.execute("DROP TYPE valutecode_old")
