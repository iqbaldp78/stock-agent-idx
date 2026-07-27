"""Ensure ihsg_predictions, ihsg_no_data, and ohlcv_no_data tables exist

Revision ID: ensure_ihsg_tables
Revises: 2da5c590cc51
Create Date: 2026-07-24 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ensure_ihsg_tables'
down_revision = '2da5c590cc51'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'ihsg_predictions' not in tables:
        op.create_table(
            'ihsg_predictions',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('run_date', sa.Date(), nullable=False),
            sa.Column('current_price', sa.Numeric(precision=12, scale=2), nullable=False),
            sa.Column('confidence', sa.String(length=10), nullable=True),
            sa.Column('direction', sa.String(length=30), nullable=True),
            sa.Column('volatility_level', sa.String(length=20), nullable=True),
            sa.Column('day_1_price', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('day_1_pct', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('day_3_price', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('day_3_pct', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('day_5_price', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('day_5_pct', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('day_7_price', sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column('day_7_pct', sa.Numeric(precision=6, scale=2), nullable=True),
            sa.Column('reasoning', sa.Text(), nullable=True),
            sa.Column('key_drivers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('risks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('component_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column('ihsg_trend', sa.String(length=30), nullable=True),
            sa.Column('macro_signal', sa.String(length=30), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ihsg_run_date', 'ihsg_predictions', [sa.literal_column('run_date DESC')], unique=False)

    if 'ihsg_no_data' not in tables:
        op.create_table(
            'ihsg_no_data',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('trade_date', sa.Date(), nullable=False, unique=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_ihsg_no_data_date', 'ihsg_no_data', ['trade_date'], unique=False)

    if 'ohlcv_no_data' not in tables:
        op.create_table(
            'ohlcv_no_data',
            sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
            sa.Column('ticker', sa.String(length=10), nullable=False),
            sa.Column('trade_date', sa.Date(), nullable=False),
            sa.Column('source', sa.String(length=20), server_default='stockbit'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('ticker', 'trade_date', 'source', name='uix_ohlcv_no_data')
        )
        op.create_index('idx_ohlcv_no_data_ticker_date', 'ohlcv_no_data', ['ticker', 'trade_date'], unique=False)
    else:
        columns = [c['name'] for c in inspector.get_columns('ohlcv_no_data')]
        if 'source' not in columns:
            op.add_column('ohlcv_no_data', sa.Column('source', sa.String(length=20), server_default='stockbit'))


def downgrade() -> None:
    pass
