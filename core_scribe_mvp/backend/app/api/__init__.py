from fastapi import APIRouter

from . import notes, visits

api_router = APIRouter()
api_router.include_router(visits.router)
api_router.include_router(notes.router)
