"""add sent_at to tickets

Revision ID: 6f7a2c4d9911
Revises: 48f579292554
Create Date: 2026-04-22 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = "6f7a2c4d9911"
down_revision = "48f579292554"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("tickets", schema=None) as batch_op:
        batch_op.drop_column("sent_at")
