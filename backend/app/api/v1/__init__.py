from app.api.v1.security_router import router as security_router
from fastapi import APIRouter
from app.api.v1 import profile, recommend, reviews, search, room, movie, images, analytics

api_router = APIRouter()
api_router.include_router(recommend.router)
api_router.include_router(search.router)
api_router.include_router(room.router)
api_router.include_router(profile.router)
api_router.include_router(reviews.router)
api_router.include_router(movie.router)
api_router.include_router(images.router)
api_router.include_router(analytics.router)


api_router.include_router(security_router)
