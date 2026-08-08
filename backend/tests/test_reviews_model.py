from app.db.models import Base, Review


def test_review_table_registered():
    assert "reviews" in Base.metadata.tables
    table = Base.metadata.tables["reviews"]
    assert {"id", "user_id", "movie_id", "rating", "text", "created_at", "updated_at"} <= set(table.columns.keys())


def test_review_constraints_registered():
    names = {constraint.name for constraint in Review.__table__.constraints}
    assert "ck_reviews_rating_range" in names
    assert "uq_reviews_user_movie" in names
