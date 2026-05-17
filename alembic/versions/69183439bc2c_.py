"""empty message

Revision ID: 69183439bc2c
Revises: 
Create Date: 2026-01-08 17:37:22.940081

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "69183439bc2c"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
    )
    op.create_table(
        "coins_confidence",
        sa.Column("coin_name", sa.String(), nullable=False),
        sa.Column("period", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True, default=0.0),
        sa.PrimaryKeyConstraint("coin_name", "period")
    )
    op.create_table(
        "exchanges",
        sa.Column("coin_name", sa.String(), nullable=False),
        sa.Column("timestamp", sa.Integer(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False, default=0.0),
        sa.PrimaryKeyConstraint("coin_name", "timestamp")
    )
    op.create_table(
        "simulations",
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("initial_fiat_amount", sa.Float(), nullable=False),
        sa.Column("updated_fiat_amount", sa.Float(), nullable=False),
        sa.Column("last_rotated_at", sa.Integer(), nullable=False),
        sa.Column("timespan_in_hours", sa.Integer(), nullable=False, default=12),
        sa.Column("operational_fee_percentage", sa.Float(), nullable=False, default=0.0),
        sa.Column("trader_pro", sa.Boolean(), nullable=False, default=False),
        sa.Column("panic_mode", sa.Boolean(), nullable=False, default=False),
        sa.Column("profit_achieved_since_last_rotation", sa.Float(), nullable=False, default=False),
    )
    op.create_table(
        "simulations_portfolio",
        sa.Column("user_id", sa.String(), sa.ForeignKey("simulations.user_id"), primary_key=True),
        sa.Column("coin", sa.String(), primary_key=True, nullable=False),
        sa.Column("amount", sa.Float(), nullable=False, default=0.0),
        sa.Column("ratio", sa.Float(), nullable=False, default=0.0),
    )
    op.create_table(
        "simulations_portfolio_history",
        sa.Column("user_id", sa.String(), sa.ForeignKey("simulations.user_id"), primary_key=True),
        sa.Column("coin", sa.String(), primary_key=True, nullable=False),
        sa.Column("timestamp", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("ratio", sa.Float(), nullable=False, default=0.0),
    )


def downgrade() -> None:
    op.drop_table("simulations_portfolio_history")
    op.drop_table("simulations_portfolio")
    op.drop_table("simulations")
    op.drop_table("exchanges")
    op.drop_table("coins_confidence")
    op.drop_table("users")

