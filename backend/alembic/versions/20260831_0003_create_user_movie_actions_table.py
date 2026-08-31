"""Create user_movie_actions table (Watchlist / Favorites).

Revision ID: 20260831_0003
Revises: 20260730_0002
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260831_0003"
down_revision: str | None = "20260730_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_movie_actions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("movie_id", sa.String(), nullable=False),
        sa.Column("interaction_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "interaction_type IN ('watchlist', 'favorite')",
            name="ck_user_movie_action_type",
        ),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "movie_id", "interaction_type", name="uq_user_movie_action_type"
        ),
    )
    op.create_index(
        op.f("ix_user_movie_actions_user_id"),
        "user_movie_actions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_movie_actions_movie_id"),
        "user_movie_actions",
        ["movie_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_movie_actions_interaction_type"),
        "user_movie_actions",
        ["interaction_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_movie_actions_interaction_type"), table_name="user_movie_actions"
    )
    op.drop_index(
        op.f("ix_user_movie_actions_movie_id"), table_name="user_movie_actions"
    )
    op.drop_index(
        op.f("ix_user_movie_actions_user_id"), table_name="user_movie_actions"
    )
    op.drop_table("user_movie_actions")
