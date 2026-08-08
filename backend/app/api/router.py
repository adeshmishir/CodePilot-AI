from fastapi import APIRouter

from app.api.endpoints import agent
from app.api.endpoints import bug_detection
from app.api.endpoints import chat
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

router.include_router(
    chat.router
)

router.include_router(
    agent.router
)

router.include_router(
    bug_detection.router
)
