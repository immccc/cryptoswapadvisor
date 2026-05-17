"""empty message

Revision ID: bff0a925fe20
Revises: 69183439bc2c
Create Date: 2026-03-06 17:58:59.583801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bff0a925fe20'
down_revision: Union[str, Sequence[str], None] = '69183439bc2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Introduce api keys for users"""
    op.add_column("users", sa.Column("api_key", sa.String(), nullable=True, index=True, unique=True))

def downgrade() -> None:
    """Remove api keys for users."""
    op.drop_column("users", "api_key")
