from app.services.llm.groq_service import GroqService
from app.services.rag.context_builder import ContextBuilder
from app.services.retrieval.retrieval_service import (
    RetrievalService,
    get_retrieval_service,
)


SYSTEM_PROMPT = (
    "You are CodePilot, an AI software engineering assistant.\n\n"
    "Answer questions about the repository using the provided "
    "repository context.\n"
    "Use the retrieved code as the primary source of truth.\n"
    "Do not invent files, functions, classes, APIs, or behavior that "
    "are not supported by the context.\n"
    "If the context does not contain enough information to answer "
    "confidently, explicitly say that the retrieved repository context "
    "is insufficient.\n"
    "When useful, mention file paths and line ranges.\n"
    "Explain the answer clearly and concisely."
)


class RAGService:
    """Orchestrate retrieval, context construction, and LLM generation."""

    def __init__(
        self,
        retrieval_service: RetrievalService,
        context_builder: ContextBuilder,
        groq_service: GroqService,
    ):
        self.retrieval_service = retrieval_service
        self.context_builder = context_builder
        self.groq_service = groq_service

    def answer(
        self,
        query: str,
        repository_id: int,
        limit: int = 5,
    ) -> dict:
        results = self.retrieval_service.search(
            query=query,
            repository_id=repository_id,
            limit=limit,
        )

        context = self.context_builder.build(results)

        user_prompt = (
            f"Developer Question:\n{query}\n\n"
            f"Repository Context:\n\n{context}"
        )

        answer = self.groq_service.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        sources = [
            {
                "file_path": result.get("file_path"),
                "symbol_name": result.get("symbol_name"),
                "start_line": result.get("start_line"),
                "end_line": result.get("end_line"),
                "score": result.get("score"),
            }
            for result in results
        ]

        return {
            "answer": answer,
            "sources": sources,
        }


rag_service: RAGService | None = None


def get_rag_service() -> RAGService:
    global rag_service

    if rag_service is None:
        rag_service = RAGService(
            retrieval_service=get_retrieval_service(),
            context_builder=ContextBuilder(),
            groq_service=GroqService(),
        )

    return rag_service
