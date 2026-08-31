"""Create the initial CineIQ database schema.

Revision ID: 20260726_0001
Revises:
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260726_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movies",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("overview", sa.Text(), nullable=True),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("poster_path", sa.String(), nullable=True),
        sa.Column("backdrop_path", sa.String(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=True),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("vote_average", sa.Float(), nullable=True),
        sa.Column("vote_count", sa.Integer(), nullable=True),
        sa.Column("dominant_emotion", sa.String(), nullable=True),
        sa.Column("emotional_arc", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_movies_id"), "movies", ["id"], unique=False)
    op.create_index(op.f("ix_movies_title"), "movies", ["title"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "interactions",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("movie_id", sa.String(), nullable=True),
        sa.Column("interaction_type", sa.String(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_interactions_movie_id"),
        "interactions",
        ["movie_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interactions_user_id"),
        "interactions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "watch_rooms",
        sa.Column(
            "id",
            sa.String(),
            nullable=False,
        ),
        sa.Column("creator_id", sa.String(), nullable=True),
        sa.Column("movie_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["movie_id"], ["movies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("watch_rooms")

    op.drop_index(
        op.f("ix_interactions_user_id"),
        table_name="interactions",
    )
    op.drop_index(
        op.f("ix_interactions_movie_id"),
        table_name="interactions",
    )
    op.drop_table("interactions")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_movies_title"), table_name="movies")
    op.drop_index(op.f("ix_movies_id"), table_name="movies")
    op.drop_table("movies")
