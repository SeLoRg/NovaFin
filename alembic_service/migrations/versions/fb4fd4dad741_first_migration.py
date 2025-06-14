"""first migration

Revision ID: fb4fd4dad741
Revises: 
Create Date: 2025-05-25 21:59:37.816256

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb4fd4dad741'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('Users',
    sa.Column('password', sa.String(), nullable=True),
    sa.Column('login', sa.String(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('email_verification_code', sa.String(), nullable=True),
    sa.Column('phone_number', sa.String(), nullable=True),
    sa.Column('two_factor_enabled', sa.Boolean(), nullable=False),
    sa.Column('two_factor_secret', sa.String(), nullable=True),
    sa.Column('auth_provider', sa.Enum('local', 'vk', 'google', name='authprovider'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_Users_email_verification_code'), 'Users', ['email_verification_code'], unique=True)
    op.create_index(op.f('ix_Users_login'), 'Users', ['login'], unique=True)
    op.create_table('currencies',
    sa.Column('code', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=False),
    sa.Column('rate_to_base', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('payment_provider_balances',
    sa.Column('provider', sa.Enum('STRIPE', 'CLOUDPAYMENTS', name='paymentworker'), nullable=False),
    sa.Column('currency', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=False),
    sa.Column('available_amount', sa.Float(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('stripe_accounts',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('stripe_account_id', sa.String(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['Users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('wallets',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['Users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_table('wallet_accounts',
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.Column('currency_code', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=False),
    sa.Column('type', sa.Enum('FIAT', 'CRYPTO', name='walletaccounttype'), nullable=False),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('wallet_id', 'currency_code', 'type', name='uq_wallet_currency_type')
    )
    op.create_table('wallet_transactions',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('currency', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=True),
    sa.Column('from_currency', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=True),
    sa.Column('to_currency', sa.Enum('RUB', 'USD', 'EUR', 'BTC', 'ETH', 'USDT', name='valutecode'), nullable=True),
    sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column('operation_type', sa.Enum('CONVERT', 'TRANSFER', 'DEPOSIT', 'WITHDRAW', name='operationtype'), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'PROCESSED', 'COMPLETED', 'FAILED', 'REVERSED', 'CANCELLED', name='transactionstatus'), server_default='PENDING', nullable=False),
    sa.Column('date', sa.DateTime(timezone=True), nullable=False),
    sa.Column('correlation_id', sa.Uuid(), nullable=True),
    sa.Column('external_id', sa.String(), nullable=True),
    sa.Column('idempotency_key', sa.String(), nullable=False),
    sa.Column('payment_worker', sa.Enum('STRIPE', 'CLOUDPAYMENTS', name='paymentworker'), nullable=True),
    sa.Column('wallet_id', sa.Integer(), nullable=False),
    sa.Column('to_wallet_id', sa.Integer(), nullable=True),
    sa.Column('from_wallet_id', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['from_wallet_id'], ['wallets.id'], ),
    sa.ForeignKeyConstraint(['to_wallet_id'], ['wallets.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['Users.id'], ),
    sa.ForeignKeyConstraint(['wallet_id'], ['wallets.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('wallet_transactions')
    op.drop_table('wallet_accounts')
    op.drop_table('wallets')
    op.drop_table('stripe_accounts')
    op.drop_table('payment_provider_balances')
    op.drop_table('currencies')
    op.drop_index(op.f('ix_Users_login'), table_name='Users')
    op.drop_index(op.f('ix_Users_email_verification_code'), table_name='Users')
    op.drop_table('Users')
    # ### end Alembic commands ###
