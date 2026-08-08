"""Regression checks for the SQLAlchemy database foundation."""

from app.db.models import Base


EXPECTED_TABLES = {
    "interactions",
    "movies",
    "users",
    "watch_rooms",
    "reviews",
}


def test_all_initial_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_interaction_foreign_keys_are_registered() -> None:
    table = Base.metadata.tables["interactions"]
    foreign_keys = {
        (foreign_key.parent.name, foreign_key.target_fullname)
        for foreign_key in table.foreign_keys
    }

    assert foreign_keys == {
        ("movie_id", "movies.id"),
        ("user_id", "users.id"),
    }


def test_watch_room_foreign_keys_are_registered() -> None:
    table = Base.metadata.tables["watch_rooms"]
    foreign_keys = {
        (foreign_key.parent.name, foreign_key.target_fullname)
        for foreign_key in table.foreign_keys
    }

    assert foreign_keys == {
        ("creator_id", "users.id"),
        ("movie_id", "movies.id"),
    }
