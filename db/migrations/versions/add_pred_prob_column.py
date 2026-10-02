"""add pred_prob column to ml_prediction_log

Kolom pred_return_pct secara historis diisi PROBABILITAS mentah [0,1] dari
klasifier (salah nama). Migrasi ini menambah kolom pred_prob sebagai rumah
yang benar untuk probabilitas dan mem-backfill dari nilai lama (baris legacy
yang tersimpan sebagai persen dinormalkan /100).

CUTOVER MAKNA pred_return_pct: sejak 2026-09-12 cron_ml_predict.py menulis
expected return sungguhan (dalam %) ke pred_return_pct, dan probabilitas ke
pred_prob. Baris era-baru dikenali dengan pred_prob IS NOT NULL AND
pred_return_pct <> pred_prob.

Revision ID: mlpredprob01
Revises: 8f512f170146
Create Date: 2026-09-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'mlpredprob01'
down_revision = '8f512f170146'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ml_prediction_log',
                  sa.Column('pred_prob', sa.Numeric(precision=6, scale=4), nullable=True))
    op.execute("""
        UPDATE ml_prediction_log
        SET pred_prob = CASE WHEN pred_return_pct <= 1.0 THEN pred_return_pct
                             ELSE pred_return_pct / 100.0 END
        WHERE pred_prob IS NULL
    """)


def downgrade():
    op.drop_column('ml_prediction_log', 'pred_prob')
