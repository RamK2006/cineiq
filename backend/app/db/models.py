"""
backend/app/db/models.py
------------------------
Refactored SQLAlchemy database models for [CineIQ](https://github.com/RamK2006/cineiq), incorporating updated WatchRoom schema support for public rooms, titles, participant limits, and tags (#209).
"""

from __future__ import annotations

import datetime
from datetime import datetime, timezone
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _generate_uuid() -> str:
    """Generate a UUID string for use as a primary key (portable across DBs)."""
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)  # Clerk ID
    email = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    interactions = relationship("Interaction", back_populates="user")
    watch_rooms = relationship("WatchRoom", back_populates="creator")
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"
    id = Column(String, primary_key=True, index=True)  # TMDB ID or string format
    title = Column(String, index=True)
    overview = Column(Text, default="")
    release_date = Column(DateTime(timezone=True), nullable=True)
    poster_path = Column(String, nullable=True)
    backdrop_path = Column(String, nullable=True)
    genres = Column(JSON, default=list)
    popularity = Column(Float, default=0.0)
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)

    dominant_emotion = Column(String, nullable=True)
    emotional_arc = Column(JSON, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    interactions = relationship("Interaction", back_populates="movie")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    movie_id = Column(String, ForeignKey("movies.id"), index=True)
    interaction_type = Column(String)  # 'view', 'like', 'dislike', 'watchlist'
    rating = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="interactions")
    movie = relationship("Movie", back_populates="interactions")


class WatchRoom(Base):
    __tablename__ = "watch_rooms"
    id = Column(String, primary_key=True, default=_generate_uuid)
    creator_id = Column(String, ForeignKey("users.id"))
    movie_id = Column(String, ForeignKey("movies.id"), nullable=True)
    
    # Updated fields for public room discovery and limits (#209)
    title = Column(String, nullable=False, default="Watch Party")
    is_public = Column(Boolean, default=True, nullable=False)
    max_participants = Column(Integer, default=10, nullable=False)
    tags = Column(JSON, default=list, nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    creator = relationship("User", back_populates="watch_rooms")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(String, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        UniqueConstraint("user_id", "movie_id", name="uq_reviews_user_movie"),
    )


class ReviewVote(Base):
    __tablename__ = "review_votes"

    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, index=True, nullable=False)
    review_id = Column(String, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    vote_type = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uq_user_review_vote"),
    )
