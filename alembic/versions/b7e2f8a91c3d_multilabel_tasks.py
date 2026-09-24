"""multilabel tasks

Revision ID: b7e2f8a91c3d
Revises: a1c4e9b27d5f
Create Date: 2026-09-22

Adds label_tasks.is_multilabel (0/1): tasks where each item can carry
several labels at once.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e2f8a91c3d'
down_revision: Union[str, Sequence[str], None] = 'a1c4e9b27d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('label_tasks', sa.Column('is_multilabel', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('label_tasks', 'is_multilabel')
