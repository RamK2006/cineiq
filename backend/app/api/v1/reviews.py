from __future__ import annotations

from datetime import datetime
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import get_current_user, fetch_clerk_user_info
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
    id: str
    user_id: str
    movie_id: str
    rating: int
    text: str
    created_at: datetime
    updated_at: datetime
    is_owner: bool = False
    reviewer_name: str | None = None
    reviewer_avatar: str | None = None


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    page: int
    limit: int
    total: int
    pages: int
    average_rating: float
    rating_count: int
    rating_distribution: dict[int, int]


async def _ensure_user_and_movie(
    db: AsyncSession,
    user_id: str,
    movie_id: str,
) -> None:
    user = await db.get(User, user_id)
    if user is None:
        user = User(id=user_id)
        db.add(user)

    if not getattr(user, "display_name", None) or not getattr(user, "avatar_url", None):
        clerk_info = await fetch_clerk_user_info(user_id)
        if clerk_info:
            user.display_name = clerk_info.get("display_name") or getattr(user, "display_name", None)
            user.avatar_url = clerk_info.get("avatar_url") or getattr(user, "avatar_url", None)

    if await db.get(Movie, movie_id) is None:
        raise HTTPException(status_code=404, detail="Movie is not in the catalogue")

    await db.flush()


async def _update_movie_rating(db: AsyncSession, movie_id: str):
    await db.flush()
    result = await db.execute(
        select(func.count(Review.id), func.avg(Review.rating)).where(
            Review.movie_id == movie_id
        )
    )
    total, average = result.one()
    total = int(total or 0)
    average = float(average or 0.0)

    movie = await db.get(Movie, movie_id)
    if movie:
        movie.vote_count = total
        movie.vote_average = round(average, 2)


def _response(review: Review, current_user_id: str | None) -> ReviewResponse:
    reviewer_name = review.user.display_name if review.user else None
    reviewer_avatar = review.user.avatar_url if review.user else None
    return ReviewResponse(
        id=str(review.id),
        user_id=review.user_id,
        movie_id=review.movie_id,
        rating=review.rating,
        text=review.text,
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_owner=current_user_id == review.user_id,
        reviewer_name=reviewer_name,
        reviewer_avatar=reviewer_avatar,
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
        await _update_movie_rating(db, movie_id)
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already reviewed this movie",
        ) from exc

    await db.refresh(review, ["user"])
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

    dist_result = await db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.movie_id == movie_id)
        .group_by(Review.rating)
    )
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r, count in dist_result.all():
        distribution[r] = count

    result = await db.execute(
        select(Review)
        .options(selectinload(Review.user))
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
        rating_distribution=distribution,
    )


@router.patch("/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
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

    await _update_movie_rating(db, review.movie_id)
    await db.commit()
    await db.refresh(review, ["user"])
    return _response(review, user_id)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: str,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    review = await db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="You can only delete your own review")

    movie_id = review.movie_id
    await db.delete(review)
    await _update_movie_rating(db, movie_id)
    await db.commit()
