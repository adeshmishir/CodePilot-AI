from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.retrieval import (
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)


router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["Search"]
)


@router.post(
    "/search",
    response_model=SearchResponse
)
def search_repository(
    repository_id: int,
    request: SearchRequest,
    db: Session = Depends(get_db),
    retrieval: RetrievalService = Depends(get_retrieval_service),
):
    repository = (
        db.query(RepositoryModel)
        .filter(RepositoryModel.id == repository_id)
        .first()
    )

    if repository is None:
        raise HTTPException(
            status_code=404,
            detail="Repository not found"
        )

    results = retrieval.search(
        query=request.query,
        repository_id=repository_id,
        limit=request.limit,
    )

    return SearchResponse(
        results=[
            SearchResult(**result)
            for result in results
        ]
    )
