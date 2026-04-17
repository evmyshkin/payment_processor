"""add payments and outbox tables

Revision ID: 5f2d5b5a6a8d
Revises:
Create Date: 2026-04-17 23:30:00.000000
"""
from collections.abc import Sequence

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5f2d5b5a6a8d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column(
            'currency',
            sa.Enum('RUB', 'USD', 'EUR', name='currency_enum'),
            nullable=False,
        ),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'succeeded', 'failed', name='payment_status_enum'),
            nullable=False,
        ),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('webhook_url', sa.String(length=2048), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_payments_idempotency_key',
        'payments',
        ['idempotency_key'],
        unique=True,
    )
    op.create_table(
        'outbox',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=128), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_outbox_aggregate_id', 'outbox', ['aggregate_id'], unique=False)
    op.create_index('ix_outbox_published_at', 'outbox', ['published_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_outbox_published_at', table_name='outbox')
    op.drop_index('ix_outbox_aggregate_id', table_name='outbox')
    op.drop_table('outbox')
    op.drop_index('ix_payments_idempotency_key', table_name='payments')
    op.drop_table('payments')
    op.execute('DROP TYPE IF EXISTS payment_status_enum')
    op.execute('DROP TYPE IF EXISTS currency_enum')
