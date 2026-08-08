from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()


def _generate_uuid() -> str:
    """Generate a UUID string for use as a primary key (portable across DBs)."""
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)  # Clerk ID
    email = Column(String, unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
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
    # Stored as JSON list of strings — portable across SQLite, PostgreSQL, etc.
    genres = Column(JSON, default=list)
    popularity = Column(Float, default=0.0)
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)

    # Emotional and semantic metadata
    dominant_emotion = Column(String, nullable=True)
    emotional_arc = Column(JSON, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    interactions = relationship("Interaction", back_populates="movie")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(String, primary_key=True, default=_generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    movie_id = Column(String, ForeignKey("movies.id"), index=True)
    interaction_type = Column(String) # 'view', 'like', 'dislike', 'watchlist'
    rating = Column(Float, nullable=True) # Explicit rating if any
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="interactions")
    movie = relationship("Movie", back_populates="interactions")


class WatchRoom(Base):
    __tablename__ = "watch_rooms"
    id = Column(String, primary_key=True, default=_generate_uuid)
    creator_id = Column(String, ForeignKey("users.id"))
    movie_id = Column(String, ForeignKey("movies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
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
