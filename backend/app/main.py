from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="CodePilot AI",
    version="0.1.0",
    description="AI Software Engineering Agent",
)

app.include_router(api_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "application": "CodePilot AI",
        "version": "0.1.0",
        "status": "running",
    }