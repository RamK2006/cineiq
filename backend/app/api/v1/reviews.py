from __future__ import annotations

from datetime import datetime
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Movie, Review, User
from app.db.session import get_db

router = APIRouter(tags=["reviews"])


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=5000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, max_length=5000)


class ReviewResponse(BaseModel):
    id: UUID
    user_id: str
    movie_id: str
    rating: int
    text: str
    created_at: datetime
    updated_at: datetime
    is_owner: bool = False


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    page: int
    limit: int
    total: int
    pages: int
    average_rating: float
    rating_count: int


async def _ensure_user_and_movie(
    db: AsyncSession,
    user_id: str,
    movie_id: str,
) -> None:
    if await db.get(User, user_id) is None:
        db.add(User(id=user_id))

    if await db.get(Movie, movie_id) is None:
        db.add(Movie(id=movie_id, title=f"TMDB Movie {movie_id}", genres=[]))

    await db.flush()


def _response(review: Review, current_user_id: str | None) -> ReviewResponse:
    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        movie_id=review.movie_id,
        rating=review.rating,
        text=review.text,
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_owner=current_user_id == review.user_id,
    )


@router.post(
    "/movies/{movie_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    movie_id: str,
    payload: ReviewCreate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_user_and_movie(db, user_id, movie_id)
    review = Review(
        user_id=user_id,
        movie_id=movie_id,
        rating=payload.rating,
        text=payload.text.strip(),
    )
    db.add(review)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this movie",
        ) from exc

    await db.refresh(review)
    return _response(review, user_id)


@router.get(
    "/movies/{movie_id}/reviews",
    response_model=ReviewListResponse,
)
async def list_reviews(
    movie_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    total_result = await db.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.movie_id == movie_id
        )
    )
    total, average = total_result.one()
    total = int(total or 0)

    result = await db.execute(
        select(Review)
        .where(Review.movie_id == movie_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    reviews = result.scalars().all()

    return ReviewListResponse(
        items=[_response(review, None) for review in reviews],
        page=page,
        limit=limit,
        total=total,
        pages=ceil(total / limit) if total else 0,
        average_rating=round(float(average or 0), 2),
        rating_count=total,
    )


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: UUID,
    payload: ReviewUpdate,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only edit your own review")

    changes = payload.model_dump(exclude_unset=True)
    if "rating" in changes:
        review.rating = changes["rating"]
    if "text" in changes:
        review.text = changes["text"].strip()

    await db.commit()
    await db.refresh(review)
    return _response(review, user_id)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own review")

    await db.delete(review)
    await db.commit()
