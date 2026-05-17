"""empty message

Revision ID: 258312cb23d0
Revises: bff0a925fe20
Create Date: 2026-03-29 22:27:39.655958

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '258312cb23d0'
down_revision: Union[str, Sequence[str], None] = 'bff0a925fe20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Introduce api keys for users"""
    op.add_column("simulations", sa.Column("webhook_endpoint", sa.String(), nullable=True, index=False, unique=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("simulations", "webhook_endpoint")
