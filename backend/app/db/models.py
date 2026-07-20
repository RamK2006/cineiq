from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from datetime import datetime, timezone

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True) # Clerk ID
    email = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    interactions = relationship("Interaction", back_populates="user")
    watch_rooms = relationship("WatchRoom", back_populates="creator")

class Movie(Base):
    __tablename__ = "movies"
    id = Column(String, primary_key=True, index=True) # TMDB ID or string format
    title = Column(String, index=True)
    overview = Column(Text)
    release_date = Column(DateTime(timezone=True), nullable=True)
    poster_path = Column(String, nullable=True)
    backdrop_path = Column(String, nullable=True)
    genres = Column(ARRAY(String))
    popularity = Column(Float, default=0.0)
    vote_average = Column(Float, default=0.0)
    vote_count = Column(Integer, default=0)
    
    # Emotional and semantic metadata
    dominant_emotion = Column(String, nullable=True)
    emotional_arc = Column(JSON, nullable=True)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    interactions = relationship("Interaction", back_populates="movie")

class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, ForeignKey("users.id"))
    movie_id = Column(String, ForeignKey("movies.id"))
    interaction_type = Column(String) # 'view', 'like', 'dislike', 'watchlist'
    rating = Column(Float, nullable=True) # Explicit rating if any
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="interactions")
    movie = relationship("Movie", back_populates="interactions")

class WatchRoom(Base):
    __tablename__ = "watch_rooms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creator_id = Column(String, ForeignKey("users.id"))
    movie_id = Column(String, ForeignKey("movies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    creator = relationship("User", back_populates="watch_rooms")
