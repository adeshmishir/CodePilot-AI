from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import router
from app.config.settings import settings
from app.core.exceptions import RepositoryCloneError, RepositoryIndexError

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Software Engineering Agent",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(RepositoryCloneError)
async def repository_clone_exception_handler(
    request: Request,
    exc: RepositoryCloneError
):
    content = {
        "success": False,
        "message": exc.message
    }

    if exc.detail:
        content["detail"] = exc.detail

    return JSONResponse(
        status_code=400,
        content=content
    )


@app.exception_handler(RepositoryIndexError)
async def repository_index_exception_handler(
    request: Request,
    exc: RepositoryIndexError
):
    content = {
        "success": False,
        "message": exc.message
    }

    if exc.detail:
        content["detail"] = exc.detail

    return JSONResponse(
        status_code=400,
        content=content
    )


@app.get("/", tags=["Root"])
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }