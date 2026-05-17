"""add functional index for simulation rotation

Revision ID: b99e089aaf80
Revises: 258312cb23d0
Create Date: 2026-04-22 18:21:38.440284

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b99e089aaf80'
down_revision: Union[str, Sequence[str], None] = '258312cb23d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Salimos del bloque de transacción por defecto de Alembic
    # para poder usar CONCURRENTLY de forma segura en producción.
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_simulation_rotation 
            ON simulations ((last_rotated_at + timespan_in_hours * 3600));
            """
        )

def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_simulation_rotation;")