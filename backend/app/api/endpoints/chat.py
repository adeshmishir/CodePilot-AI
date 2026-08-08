import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
)
from app.services.rag.rag_service import RAGService, get_rag_service


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/repositories/{repository_id}",
    tags=["Chat"]
)


@router.post(
    "/chat",
    response_model=ChatResponse
)
def chat_repository(
    repository_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
    rag: RAGService = Depends(get_rag_service),
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

    try:
        result = rag.answer(
            query=request.query,
            repository_id=repository_id,
            limit=request.limit,
        )
    except Exception as error:
        logger.error(
            "Chat failed for repository %s: %s",
            repository_id,
            error,
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to generate an answer at this time.",
        ) from error

    return ChatResponse(
        answer=result["answer"],
        sources=[
            ChatSource(**source)
            for source in result["sources"]
        ],
    )
