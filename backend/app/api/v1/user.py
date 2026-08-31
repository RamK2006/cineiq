"""User-level movie actions: personal Watchlist and Favorites.

Endpoints (all require a valid Clerk JWT):

    POST   /api/v1/user/watchlist/{movie_id}    Add to Watchlist
    DELETE /api/v1/user/watchlist/{movie_id}    Remove from Watchlist
    GET    /api/v1/user/watchlist               List Watchlist (paginated)
    POST   /api/v1/user/favorites/{movie_id}    Mark as Favorite
    DELETE /api/v1/user/favorites/{movie_id}    Remove Favorite
    GET    /api/v1/user/favorites               List Favorites (paginated)
"""

from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Movie, User, UserMovieAction
from app.db.session import get_db

router = APIRouter(prefix="/user", tags=["user"])

VALID_ACTION_TYPES = ("watchlist", "favorite")


# ─── Response Models ─────────────────────────────────────────────────────────


class MovieSummary(BaseModel):
    id: str
    title: Optional[str] = None
    overview: str = ""
    release_date: Optional[datetime] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    genres: List[str] = []
    popularity: float = 0.0
    vote_average: float = 0.0
    vote_count: int = 0

    @classmethod
    def from_model(cls, movie: Movie) -> "MovieSummary":
        return cls(
            id=movie.id,
            title=movie.title,
            overview=movie.overview or "",
            release_date=movie.release_date,
            poster_path=movie.poster_path,
            backdrop_path=movie.backdrop_path,
            genres=[str(g) for g in (movie.genres or [])],
            popularity=float(movie.popularity or 0.0),
            vote_average=float(movie.vote_average or 0.0),
            vote_count=int(movie.vote_count or 0),
        )


class UserMovieActionItem(BaseModel):
    movie: MovieSummary
    added_at: datetime


class UserMovieActionListResponse(BaseModel):
    items: List[UserMovieActionItem]
    page: int
    limit: int
    total: int
    pages: int


class UserMovieActionResponse(BaseModel):
    message: str
    action: UserMovieActionItem


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _action_label(action_type: str) -> str:
    return "Watchlist" if action_type == "watchlist" else "Favorites"


def _action_phrase(action_type: str) -> str:
    return "watchlist" if action_type == "watchlist" else "favorites"


async def _ensure_user_and_movie(
    db: AsyncSession,
    user_id: str,
    movie_id: str,
) -> Movie:
    """Make sure the user row exists and the movie is in the catalogue."""
    if await db.get(User, user_id) is None:
        db.add(User(id=user_id))

    movie = await db.get(Movie, movie_id)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie is not in the catalogue",
        )

    await db.flush()
    return movie


def _item_from_rows(action: UserMovieAction, movie: Movie) -> UserMovieActionItem:
    return UserMovieActionItem(movie=MovieSummary.from_model(movie), added_at=action.created_at)


async def _add_action(
    db: AsyncSession, user_id: str, movie_id: str, action_type: str
) -> tuple[UserMovieAction, bool, Movie]:
    """Idempotently add an action. Returns (action, newly_created, movie)."""
    movie = await _ensure_user_and_movie(db, user_id, movie_id)

    stmt = select(UserMovieAction).where(
        UserMovieAction.user_id == user_id,
        UserMovieAction.movie_id == movie_id,
        UserMovieAction.interaction_type == action_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing, False, movie

    action = UserMovieAction(
        user_id=user_id, movie_id=movie_id, interaction_type=action_type
    )
    db.add(action)
    try:
        await db.commit()
    except IntegrityError:
        # Unique constraint raced us — re-fetch the winner of the race.
        await db.rollback()
        action = (await db.execute(stmt)).scalar_one_or_none()
        if action is None:
            raise
        return action, False, movie

    await db.refresh(action)
    return action, True, movie


async def _remove_action(
    db: AsyncSession, user_id: str, movie_id: str, action_type: str
) -> None:
    stmt = select(UserMovieAction).where(
        UserMovieAction.user_id == user_id,
        UserMovieAction.movie_id == movie_id,
        UserMovieAction.interaction_type == action_type,
    )
    action = (await db.execute(stmt)).scalar_one_or_none()
    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie is not in your {_action_phrase(action_type)}",
        )
    await db.delete(action)
    await db.commit()


async def _list_actions(
    db: AsyncSession, user_id: str, action_type: str, page: int, limit: int
) -> UserMovieActionListResponse:
    total = (
        await db.execute(
            select(func.count(UserMovieAction.id)).where(
                UserMovieAction.user_id == user_id,
                UserMovieAction.interaction_type == action_type,
            )
        )
    ).scalar()
    total = int(total or 0)

    rows = (
        await db.execute(
            select(UserMovieAction, Movie)
            .join(Movie, UserMovieAction.movie_id == Movie.id)
            .where(
                UserMovieAction.user_id == user_id,
                UserMovieAction.interaction_type == action_type,
            )
            .order_by(UserMovieAction.created_at.desc(), UserMovieAction.id.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
    ).all()

    items = [_item_from_rows(action, movie) for action, movie in rows]
    return UserMovieActionListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=ceil(total / limit) if total else 0,
    )


# ─── Watchlist Endpoints ─────────────────────────────────────────────────────


@router.post(
    "/watchlist/{movie_id}",
    response_model=UserMovieActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_watchlist(
    movie_id: str,
    response: Response,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a movie to the authenticated user's personal Watchlist."""
    action, newly_created, movie = await _add_action(db, user_id, movie_id, "watchlist")
    if not newly_created:
        response.status_code = status.HTTP_200_OK
    return UserMovieActionResponse(
        message=(
            "Added to Watchlist"
            if newly_created
            else "Already in your Watchlist"
        ),
        action=_item_from_rows(action, movie),
    )


@router.delete("/watchlist/{movie_id}", status_code=status.HTTP_200_OK)
async def remove_from_watchlist(
    movie_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a movie from the authenticated user's Watchlist."""
    await _remove_action(db, user_id, movie_id, "watchlist")
    return {"message": "Removed from Watchlist"}


@router.get("/watchlist", response_model=UserMovieActionListResponse)
async def list_watchlist(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's Watchlist movies with pagination."""
    return await _list_actions(db, user_id, "watchlist", page, limit)


# ─── Favorites Endpoints ─────────────────────────────────────────────────────


@router.post(
    "/favorites/{movie_id}",
    response_model=UserMovieActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_favorites(
    movie_id: str,
    response: Response,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a movie as Favorite for the authenticated user."""
    action, newly_created, movie = await _add_action(db, user_id, movie_id, "favorite")
    if not newly_created:
        response.status_code = status.HTTP_200_OK
    return UserMovieActionResponse(
        message=(
            "Added to Favorites"
            if newly_created
            else "Already in your Favorites"
        ),
        action=_item_from_rows(action, movie),
    )


@router.delete("/favorites/{movie_id}", status_code=status.HTTP_200_OK)
async def remove_from_favorites(
    movie_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a Favorite for the authenticated user."""
    await _remove_action(db, user_id, movie_id, "favorite")
    return {"message": "Removed from Favorites"}


@router.get("/favorites", response_model=UserMovieActionListResponse)
async def list_favorites(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=50),
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the authenticated user's Favorite movies with pagination."""
    return await _list_actions(db, user_id, "favorite", page, limit)
