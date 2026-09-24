"""email verification + otp codes

Revision ID: d9f3a7b15e2c
Revises: c8d1e6f42a9b
Create Date: 2026-09-22

users.email_verified (existing rows default to verified so current
accounts keep working); new otp_codes table for signup verification
and OTP login.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9f3a7b15e2c'
down_revision: Union[str, Sequence[str], None] = 'c8d1e6f42a9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Integer(), nullable=False, server_default='1'),
    )
    op.create_table('otp_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('purpose', sa.String(length=20), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('consumed', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_otp_codes_email', 'otp_codes', ['email'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_otp_codes_email', table_name='otp_codes')
    op.drop_table('otp_codes')
    op.drop_column('users', 'email_verified')
