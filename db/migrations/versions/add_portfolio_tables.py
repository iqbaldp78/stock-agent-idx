"""add portfolio_holdings, dca_transactions, dca_strategy tables

Revision ID: portfolio_001
Revises: broker_cols_001
Create Date: 2026-06-13 10:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'portfolio_001'
down_revision = 'broker_cols_001'
branch_labels = None
depends_on = None


def upgrade():
    # === portfolio_holdings ===
    op.create_table(
        'portfolio_holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('avg_cost', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_shares', sa.Integer(), nullable=False),
        sa.Column('total_invested', sa.Numeric(15, 2), nullable=True),
        sa.Column('current_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('current_value', sa.Numeric(15, 2), nullable=True),
        sa.Column('unrealized_pnl', sa.Numeric(15, 2), nullable=True),
        sa.Column('unrealized_pnl_pct', sa.Numeric(6, 2), nullable=True),
        sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Date(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.Date(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticker'),
    )

    # === dca_transactions ===
    op.create_table(
        'dca_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('holding_id', sa.Integer(), nullable=True),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('transaction_type', sa.String(10), nullable=False),
        sa.Column('shares', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('broker_fee', sa.Numeric(10, 2), server_default='0', nullable=True),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.Date(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['holding_id'], ['portfolio_holdings.id']),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # === dca_strategy ===
    op.create_table(
        'dca_strategy',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('holding_id', sa.Integer(), nullable=True),
        sa.Column('total_budget', sa.Numeric(15, 2), nullable=False),
        sa.Column('remaining_budget', sa.Numeric(15, 2), nullable=True),
        sa.Column('dca_count', sa.Integer(), server_default='3', nullable=True),
        sa.Column('entry_low', sa.Numeric(12, 2), nullable=True),
        sa.Column('entry_high', sa.Numeric(12, 2), nullable=True),
        sa.Column('max_entry', sa.Numeric(12, 2), nullable=True),
        sa.Column('next_buy_price', sa.Numeric(12, 2), nullable=True),
        sa.Column('signal_id', sa.Integer(), nullable=True),
        sa.Column('tp1', sa.Numeric(12, 2), nullable=True),
        sa.Column('tp2', sa.Numeric(12, 2), nullable=True),
        sa.Column('tp3', sa.Numeric(12, 2), nullable=True),
        sa.Column('stop_loss', sa.Numeric(12, 2), nullable=True),
        sa.Column('status', sa.String(20), server_default='ACTIVE', nullable=True),
        sa.Column('activated_at', sa.Date(), nullable=True),
        sa.Column('completed_at', sa.Date(), nullable=True),
        sa.Column('created_at', sa.Date(), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['holding_id'], ['portfolio_holdings.id']),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('dca_strategy')
    op.drop_table('dca_transactions')
    op.drop_table('portfolio_holdings')
