from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config.settings import settings
from app.database.session import engine

router = APIRouter()


@router.get("/health", tags=["Health"])
def health_check(response: Response):
    """
    Health check endpoint that verifies the API and its dependencies are up.
    """
    checks = {
        "database": False,
        "vector_store": False,
    }

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        pass

    if settings.QDRANT_URL == ":memory:":
        checks["vector_store"] = True
    else:
        try:
            from app.services.vector.vector_store import get_vector_store

            get_vector_store().health_check()
            checks["vector_store"] = True
        except Exception:
            pass

    healthy = all(checks.values())

    if not healthy:
        response.status_code = 503

    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": checks,
    }
