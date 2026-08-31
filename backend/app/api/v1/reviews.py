from __future__ import annotations

from datetime import datetime
from math import ceil
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import Movie, Review, ReviewVote, User
from app.db.session import get_db

router = APIRouter(tags=["reviews"])


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=5000)


class ReviewUpdate(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = Field(default=None, max_length=5000)


class VotePayload(BaseModel):
    vote_type: int  # +1 or -1


class ReviewResponse(BaseModel):
    id: str
    user_id: str
    movie_id: str
    rating: int
    text: str
    created_at: datetime
    updated_at: datetime
    is_owner: bool = False
    helpful_count: int = 0
    user_vote: int = 0


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
        raise HTTPException(status_code=404, detail="Movie is not in the catalogue")

    await db.flush()


def _response(
    review: Review,
    current_user_id: str | None = None,
    helpful_count: int = 0,
    user_vote: int = 0,
) -> ReviewResponse:
    return ReviewResponse(
        id=str(review.id),
        user_id=review.user_id,
        movie_id=review.movie_id,
        rating=review.rating,
        text=review.text,
        created_at=review.created_at,
        updated_at=review.updated_at,
        is_owner=current_user_id == review.user_id,
        helpful_count=helpful_count,
        user_vote=user_vote,
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
    current_user_id: Optional[str] = Query(default=None),
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

    items: list[ReviewResponse] = []
    for review in reviews:
        helpful_res = await db.execute(
            select(func.count(ReviewVote.id)).where(
                ReviewVote.review_id == review.id,
                ReviewVote.vote_type == 1,
            )
        )
        helpful_count = helpful_res.scalar() or 0

        user_vote = 0
        if current_user_id:
            uv_res = await db.execute(
                select(ReviewVote.vote_type).where(
                    ReviewVote.review_id == review.id,
                    ReviewVote.user_id == current_user_id,
                )
            )
            user_vote = uv_res.scalar_one_or_none() or 0

        items.append(_response(review, current_user_id, helpful_count, user_vote))

    return ReviewListResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        pages=ceil(total / limit) if total else 0,
        average_rating=round(float(average or 0), 2),
        rating_count=total,
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

    await db.commit()
    await db.refresh(review)
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

    await db.delete(review)
    await db.commit()


@router.post("/reviews/{review_id}/vote", status_code=status.HTTP_200_OK)
@router.post("/api/v1/reviews/{review_id}/vote", status_code=status.HTTP_200_OK)
async def vote_review(
    review_id: str,
    payload: VotePayload,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggles or flips an authenticated user's helpfulness vote on a target review item.
    Enforces spam resilience through strict database constraints.
    """
    if payload.vote_type not in (1, -1):
        raise HTTPException(status_code=400, detail="Invalid vote type configuration token.")

    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Target review resource not found.")

    stmt = select(ReviewVote).where(
        ReviewVote.user_id == user_id,
        ReviewVote.review_id == review_id
    )
    result = await db.execute(stmt)
    existing_vote = result.scalar_one_or_none()

    if existing_vote:
        if existing_vote.vote_type == payload.vote_type:
            # If the same button is pressed twice, undo the vote completely (retract)
            await db.delete(existing_vote)
            await db.commit()
            return {"message": "Vote retracted successfully.", "user_vote": 0}
        else:
            # If the user switches their vote (e.g., from +1 to -1), update it in place
            existing_vote.vote_type = payload.vote_type
            await db.commit()
            return {"message": "Vote flipped successfully.", "user_vote": payload.vote_type}
    else:
        # Create a fresh vote record
        new_vote = ReviewVote(
            user_id=user_id,
            review_id=review_id,
            vote_type=payload.vote_type
        )
        db.add(new_vote)
        await db.commit()
        return {"message": "Vote recorded successfully.", "user_vote": payload.vote_type}

