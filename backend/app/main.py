from fastapi import FastAPI

from app.api.router import api_router
from app.config.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Software Engineering Agent",
    debug=settings.DEBUG,
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }