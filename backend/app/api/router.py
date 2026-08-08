from fastapi import APIRouter

from app.api.endpoints import health
from app.api.endpoints import repositories
from app.api.endpoints import search


router = APIRouter()

router.include_router(
    health.router
)

router.include_router(
    repositories.router
)

router.include_router(
    search.router
)
