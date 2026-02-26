"""Initial migration - users and cars tables

Revision ID: 001
Revises: 
Create Date: 2025-02-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("brand", sa.String(100), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("price", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(100), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cars_brand"), "cars", ["brand"], unique=False)
    # MySQL TEXT columns can't have a regular unique index, use a prefix
    op.execute("CREATE UNIQUE INDEX uq_cars_url ON cars (url(500))")


def downgrade() -> None:
    op.drop_index("uq_cars_url", table_name="cars")
    op.drop_index(op.f("ix_cars_brand"), table_name="cars")
    op.drop_table("cars")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_table("users")
