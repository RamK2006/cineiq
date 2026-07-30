from fastapi import APIRouter
from app.api.v1 import profile, recommend, search, room
from backend.app.api.v1 import movies

api_router = APIRouter()
api_router.include_router(movies.router)
api_router.include_router(recommend.router)
api_router.include_router(search.router)
api_router.include_router(room.router)

api_router.include_router(profile.router)
