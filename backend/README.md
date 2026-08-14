# CodePilot AI — Backend

FastAPI backend for CodePilot, an AI software engineering agent. It clones
GitHub repositories, indexes their code into PostgreSQL + Qdrant, and exposes
REST/SSE endpoints for RAG chat, semantic search, single/multi-agent
execution, bug detection, PR review, and issue triage.

## Stack

- Python 3.13, FastAPI, Uvicorn
- SQLAlchemy 2 + PostgreSQL 16 (Alembic migrations)
- Qdrant vector store (in-memory for dev, persistent for production)
- FastEmbed (`BAAI/bge-small-en-v1.5`) for ONNX embeddings
- tree-sitter for AST parsing and symbol extraction
- Groq (`llama-3.3-70b-versatile`) for all LLM calls
- Managed with `uv`

## Structure

```
app/
├── agents/          # Single-agent service, planner, prompts, state
├── api/             # Routers & endpoint modules
│   └── endpoints/   # health, repositories, search, chat, agent, bugs, github
├── config/          # Pydantic settings (env-based)
├── core/            # Exceptions, memory logging
├── database/        # Engine, session, Base
├── models/          # RepositoryModel, CodeChunkModel
├── schemas/         # Pydantic request/response schemas
├── services/
│   ├── embedding/   # FastEmbed embedding service
│   ├── github/      # Git clone service + GitHub REST client, PR/issue AI
│   ├── indexing/    # RepositoryIndexer, VectorIndexer
│   ├── llm/         # Groq service (sync + streaming)
│   ├── parser/      # tree-sitter code parsing, language mapping, repo parser
│   ├── rag/         # RAG service, context builder, query classifier
│   ├── repository/  # Clone progress, path helpers, repository service
│   ├── retrieval/   # Query → vector search orchestration
│   └── vector/      # Qdrant vector store
├── tools/           # Agent tools: search_repository, list_repository_files,
│                    #   get_code_context + ToolRegistry
├── workflows/
│   ├── bug_detection/  # Bug analysis workflow
│   └── multi_agent/    # Multi-agent orchestrator (researcher/bug_hunter/executor)
└── main.py          # FastAPI app entry point
alembic/             # Database migrations
tests/               # pytest suite (agents, api, config, services, tools, workflows)
```

## Getting started

```bash
uv sync                 # install dependencies
cp .env.example .env    # configure environment
uv run alembic upgrade head   # apply migrations (requires DATABASE_URL)
uv run uvicorn app.main:app --reload --port 8000
```

Interactive API docs: `http://127.0.0.1:8000/docs`

## Environment variables

Copy `backend/.env.example` to `backend/.env`. Key variables:

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes (AI features) | Groq API key |
| `GITHUB_TOKEN` | GitHub features | Classic PAT with `repo` scope |
| `DATABASE_URL` | Persistence | PostgreSQL connection string |
| `QDRANT_URL` | No | `:memory:` (dev) or `http://qdrant:6333` (prod); must be persistent when `DEBUG=False` |
| `CORS_ORIGINS` | No | JSON list of allowed origins |
| `EMBEDDING_MODEL` | No | FastEmbed model (default `BAAI/bge-small-en-v1.5`) |
| `GROQ_MODEL` | No | Groq model (default `llama-3.3-70b-versatile`) |
| `DEBUG` | No | Enables in-memory Qdrant fallback |
| `HOST` / `PORT` | No | Bind address/port |
| `RAG_CONTEXT_MAX_CHARS` | No | Max context chars injected into RAG prompts |
| `AGENT_MAX_STEPS` | No | Max tool steps per agent run |
| `INDEX_BATCH_SIZE` | No | Embedding batch size during indexing |
| `MAX_INDEX_FILE_SIZE_MB` | No | Max indexed file size |
| `MAX_INDEX_FILES` | No | Cap on indexed files per repository |

## API endpoints

- `GET /health` — API, database, and vector store health
- `GET /` — app metadata
- `GET /repositories` — list repositories
- `POST /repositories/clone` — clone + index (async, returns `job_id`)
- `GET /repositories/clone/status/{job_id}` — clone progress
- `POST /repositories/clone/cancel/{job_id}` — cancel clone
- `POST /repositories/{id}/reindex` — re-index
- `DELETE /repositories/{id}` — delete repository
- `POST /api/repositories/{id}/search` — semantic code search
- `POST /api/repositories/{id}/chat` — RAG chat
- `POST /api/repositories/{id}/chat/stream` — SSE streaming chat
- `POST /api/repositories/{id}/agent` — single/multi-agent (`mode` field)
- `POST /api/repositories/{id}/bugs` — bug detection
- `GET /api/repositories/{id}/github/prs` — open PRs
- `POST /api/repositories/{id}/github/prs/{n}/review` — PR review
- `GET /api/repositories/{id}/github/issues` — open issues
- `POST /api/repositories/{id}/github/issues/triage` — issue triage

## Tests

```bash
uv run pytest
```

## Docker

Built and orchestrated from the repo root via `docker-compose.yml`. The image
installs git, syncs deps with `uv`, and runs `alembic upgrade head` before
starting Uvicorn.

```bash
docker compose up --build -d
```
