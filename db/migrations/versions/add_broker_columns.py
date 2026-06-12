"""add broker_true_costs and broker_distributors columns

Revision ID: broker_cols_001
Revises: 4bbaa11f38cf
Create Date: 2026-06-12 09:12:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'broker_cols_001'
down_revision = '4bbaa11f38cf'
branch_labels = None
depends_on = None


def upgrade():
    # Add broker_true_costs and broker_distributors JSONB columns
    op.add_column('signals', sa.Column('broker_true_costs', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('signals', sa.Column('broker_distributors', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    # Remove columns
    op.drop_column('signals', 'broker_distributors')
    op.drop_column('signals', 'broker_true_costs')
