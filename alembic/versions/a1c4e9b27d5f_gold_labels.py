"""gold labels for quality control

Revision ID: a1c4e9b27d5f
Revises: 9b3e7a1c4f2d
Create Date: 2026-09-22

Adds data_items.gold_label (nullable JSON): items with a known-correct
answer used to score labeler accuracy.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e9b27d5f'
down_revision: Union[str, Sequence[str], None] = '9b3e7a1c4f2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('data_items', sa.Column('gold_label', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('data_items', 'gold_label')
