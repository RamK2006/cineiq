from fastapi import APIRouter
from app.api.v1 import movies, recommend, search, room

api_router = APIRouter()
api_router.include_router(movies.router)
api_router.include_router(recommend.router)
api_router.include_router(search.router)
api_router.include_router(room.router)
