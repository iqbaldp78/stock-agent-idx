"""add users table

Revision ID: users_001
Revises: portfolio_001
Create Date: 2026-07-10 01:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'users_001'
down_revision = 'portfolio_001'

def upgrade() -> None:
    # create table if not exists users
    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users;")
