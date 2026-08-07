from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config.settings import settings
from app.core.exceptions import RepositoryCloneError

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Software Engineering Agent",
    debug=settings.DEBUG,
)

app.include_router(api_router)


@app.exception_handler(RepositoryCloneError)
async def repository_clone_exception_handler(
    request: Request,
    exc: RepositoryCloneError
):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "message": exc.message
        }
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }