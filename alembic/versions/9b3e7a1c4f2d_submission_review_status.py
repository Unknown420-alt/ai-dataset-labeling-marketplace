"""submission review status

Revision ID: 9b3e7a1c4f2d
Revises: 6cea99c70951
Create Date: 2026-09-22

Adds label_submissions.status (pending/accepted/rejected) for the owner
review queue.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9b3e7a1c4f2d'
down_revision: Union[str, Sequence[str], None] = '6cea99c70951'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'label_submissions',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('label_submissions', 'status')
