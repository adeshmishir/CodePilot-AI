import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.agent import AgentService, get_agent_service
from app.database.session import get_db
from app.models.repository import RepositoryModel
from app.schemas.agent import (
    AgentRequest,
    AgentResponse,
    AgentToolCall,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/repositories/{repository_id}",
    tags=["Agent"]
)


@router.post(
    "/agent",
    response_model=AgentResponse
)
def run_agent(
    repository_id: int,
    request: AgentRequest,
    db: Session = Depends(get_db),
    agent: AgentService = Depends(get_agent_service),
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
        result = agent.run(
            db=db,
            repository_id=repository_id,
            query=request.query,
            max_steps=request.max_steps,
        )
    except Exception as error:
        logger.error(
            "Agent failed for repository %s: %s",
            repository_id,
            error,
        )
        raise HTTPException(
            status_code=500,
            detail="The agent failed to complete the request.",
        ) from error

    return AgentResponse(
        answer=result["answer"],
        plan=result["plan"],
        tool_calls=[
            AgentToolCall(**call)
            for call in result["tool_calls"]
        ],
        observations=result["observations"],
    )
