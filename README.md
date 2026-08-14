# CodePilot AI

An AI software engineering agent. Clone a GitHub repository, index its code,
and then chat, search, run single or multi-agent investigations, detect bugs,
review pull requests, and triage issues against it — all from a web UI.

- **Frontend:** React + Vite + TypeScript + Tailwind CSS + shadcn/ui
- **Backend:** FastAPI + SQLAlchemy + PostgreSQL + Qdrant + tree-sitter + Groq
- **AI:** RAG chat, single/multi-agent execution, bug detection, PR review, issue triage

---

## Features

- **Repository ingestion** — paste any public GitHub URL; the backend clones it
  (optionally authenticated with `GITHUB_TOKEN`), parses the source with
  tree-sitter, extracts symbols, generates semantic code chunks, embeds them,
  and stores vectors in Qdrant. Clone/index runs in a background thread with a
  live progress bar (start / status / cancel endpoints).
- **Repository-aware RAG chat** — ask questions about the codebase. A query
  classifier decides whether a question needs repository context; when it does,
  relevant code chunks are retrieved and grounded into the LLM prompt. Answers
  cite file paths and line ranges. Streaming SSE chat is also supported.
- **Semantic code search** — natural-language search over the indexed code via
  vector similarity, returning ranked symbols with file paths, line ranges,
  scores, and content.
- **Agent mode (single & multi)** — an LLM planner builds a tool-based plan and
  executes steps against repository tools (`search_repository`,
  `list_repository_files`, `get_code_context`). In `multi` mode an orchestrator
  routes the request to specialist agents — researcher, bug hunter, and tool
  executor — then synthesizes their reports into a single answer.
- **Bug detection** — retrieves the most relevant code for a query and has the
  LLM produce structured, severity-ranked findings with evidence and
  recommendations.
- **GitHub integration** — list open pull requests, get an AI pull request
  review (structured, severity-ranked comments), list open issues, and get AI
  issue triage (category, severity, and suggested labels).
- **Repository management** — list, re-index, and delete repositories from the
  API or the frontend sidebar.

## How it works (pipeline)

```
User (React frontend)
  │
  ▼
FastAPI (REST / SSE)
  │
  ├── Repository ingestion
  │     GitHub URL → git clone → tree-sitter AST parse →
  │     symbol/chunk extraction → FastEmbed embeddings → Qdrant vectors
  │     + code chunks persisted in PostgreSQL (Alembic-managed)
  │
  ├── Retrieval
  │     query → embedding → Qdrant similarity search → ranked chunks
  │
  ├── RAG chat
  │     query classifier → (retrieval + context builder) → Groq LLM → answer
  │
  └── Agents & workflows
        planner → tool registry (search / list files / code context)
        multi-agent orchestrator → researcher · bug_hunter · executor
        GitHub client → PR review · issue triage
```

## Repository structure

```
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── agents/          # Single-agent service, planner, prompts, state
│   │   ├── api/             # FastAPI routers & endpoint modules
│   │   ├── config/          # Pydantic settings (env-based)
│   │   ├── core/            # Exceptions, memory logging
│   │   ├── database/        # SQLAlchemy engine, session, Base
│   │   ├── models/          # Repository & CodeChunk ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── embedding/   # FastEmbed (ONNX) embedding service
│   │   │   ├── github/      # Git service + GitHub REST client, PR/issue AI
│   │   │   ├── indexing/    # Repository & vector indexers
│   │   │   ├── llm/         # Groq LLM service (sync + streaming)
│   │   │   ├── parser/      # tree-sitter parsing + language mapping
│   │   │   ├── rag/         # RAG service, context builder, query classifier
│   │   │   ├── repository/  # Repository lifecycle (clone progress, paths)
│   │   │   ├── retrieval/   # Query → vector search orchestration
│   │   │   └── vector/      # Qdrant vector store
│   │   ├── tools/           # Agent tool registry and tool implementations
│   │   ├── workflows/
│   │   │   ├── bug_detection/  # Bug analysis workflow
│   │   │   └── multi_agent/    # Multi-agent orchestrator
│   │   └── main.py          # FastAPI app entry point
│   ├── alembic/             # Database migrations
│   ├── tests/               # pytest suite
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── uv.lock
│   └── .env.example
├── frontend/                # React + Vite + TypeScript app
│   ├── src/
│   │   ├── components/      # Chat, Search, Agent, Bug Detection, GitHub tabs,
│   │   │                    # repository sidebar, UI primitives
│   │   ├── context/         # Workspace & theme providers
│   │   ├── hooks/           # Async submit, repository reset
│   │   ├── lib/             # Typed API client, error formatting
│   │   ├── types/           # Shared API types mirroring backend schemas
│   │   └── test/            # Vitest setup
│   ├── Dockerfile           # Build + nginx serve
│   ├── nginx.conf           # SPA + API reverse proxy
│   └── .env.example
├── docker-compose.yml       # PostgreSQL + Qdrant + backend + frontend
└── docs/                    # ARCHITECTURE, ROADMAP, CHANGELOG, DECISIONS
```

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite, TypeScript, Tailwind CSS 4, shadcn/ui (Radix), lucide-react |
| Backend | Python 3.13, FastAPI, Uvicorn |
| ORM / DB | SQLAlchemy 2, PostgreSQL 16, Alembic |
| Vector DB | Qdrant (in-memory for dev, persistent for production) |
| Embeddings | FastEmbed `BAAI/bge-small-en-v1.5` (ONNX, 384-dim) |
| Code parsing | tree-sitter + tree-sitter-language-pack |
| LLM | Groq (`llama-3.3-70b-versatile`) |
| Tooling | uv, pytest, oxlint, Vitest, Docker Compose |

## Local development

### Prerequisites

- Python 3.13+
- Node.js 22+
- PostgreSQL (optional for local dev — see `DATABASE_URL` below)
- Qdrant (optional — in-memory mode is fine for development)

### Backend

From `backend/`:

```bash
# create a virtualenv and install dependencies (uv recommended)
uv sync

# or with pip + requirements.txt
pip install -r requirements.txt

# configure environment
cp .env.example .env

# run migrations (only when DATABASE_URL is set)
uv run alembic upgrade head

# start the API
uv run uvicorn app.main:app --reload --port 8000
# (or: .venv\Scripts\python -m uvicorn app.main:app --reload --port 8000)
```

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

### Frontend

From `frontend/`:

```bash
npm install
cp .env.example .env   # VITE_API_URL defaults to http://localhost:8000
npm run dev            # serves at http://localhost:5173
```

### Environment variables

Backend (`backend/.env`) — copy from `backend/.env.example`:

| Variable | Required | Description |
| --- | --- | --- |
| `GROQ_API_KEY` | Yes (all AI features) | Groq API key for chat, agent, bugs, triage, review |
| `GITHUB_TOKEN` | For GitHub features | Classic personal access token with `repo` scope (`public_repo` for public repos). Used for clone auth, PR review, and issue triage |
| `DATABASE_URL` | For persistence | PostgreSQL connection string (e.g. `postgresql+psycopg://user:pass@localhost:5432/codepilot`) |
| `QDRANT_URL` | No | `:memory:` (default) for local in-memory vectors, else a running Qdrant instance (`http://localhost:6333`). Must be persistent when `DEBUG=False` |
| `CORS_ORIGINS` | No | JSON list of allowed browser origins (e.g. `["http://localhost:5173"]`) |
| `EMBEDDING_MODEL` | No | FastEmbed model (default `BAAI/bge-small-en-v1.5`) |
| `GROQ_MODEL` | No | Groq model (default `llama-3.3-70b-versatile`) |
| `DEBUG` | No | Enables in-memory Qdrant fallback and verbose settings |
| `HOST` / `PORT` | No | Bind address/port (default `127.0.0.1:8000`) |
| `APP_NAME` / `APP_VERSION` | No | App metadata |
| `RAG_CONTEXT_MAX_CHARS` | No | Max chars of context injected into RAG prompts |
| `AGENT_MAX_STEPS` | No | Max tool steps per agent run |
| `INDEX_BATCH_SIZE` | No | Embedding batch size during indexing |
| `MAX_INDEX_FILE_SIZE_MB` | No | Skip files larger than this when indexing |
| `MAX_INDEX_FILES` | No | Cap on indexed files per repository |

Frontend (`frontend/.env`) — copy from `frontend/.env.example`:

| Variable | Description |
| --- | --- |
| `VITE_API_URL` | Backend base URL (default `http://localhost:8000`; production build falls back to the hosted backend) |

### Running tests

Backend (`backend/`):

```bash
uv run pytest
```

Frontend (`frontend/`):

```bash
npm run lint     # oxlint
npm run test     # vitest run
npm run build    # tsc -b && vite build
```

## API reference

Interactive docs: `http://127.0.0.1:8000/docs` (Swagger UI)

**Repositories**

- `GET /repositories` — list indexed repositories
- `POST /repositories/clone` — clone and index a GitHub repo (async; returns `job_id`)
- `GET /repositories/clone/status/{job_id}` — poll clone/index progress
- `POST /repositories/clone/cancel/{job_id}` — cancel a running clone
- `POST /repositories/{repository_id}/reindex` — re-index a repository
- `DELETE /repositories/{repository_id}` — delete a repository and its data

**Search & chat**

- `POST /api/repositories/{id}/search` — semantic code search
- `POST /api/repositories/{id}/chat` — repository-aware RAG chat
- `POST /api/repositories/{id}/chat/stream` — SSE streaming chat (events: `sources`, `delta`, `done`, `error`)

**Agents & bugs**

- `POST /api/repositories/{id}/agent` — single or multi-agent execution (`mode: "single" | "multi"`)
- `POST /api/repositories/{id}/bugs` — bug detection with structured findings

**GitHub**

- `GET /api/repositories/{id}/github/prs` — open pull requests
- `POST /api/repositories/{id}/github/prs/{n}/review` — AI review of a pull request
- `GET /api/repositories/{id}/github/issues` — open issues
- `POST /api/repositories/{id}/github/issues/triage` — AI triage of open issues

**Health**

- `GET /health` — checks API, database, and vector store reachability

## Production deployment (Docker)

Requires Docker. Set `GROQ_API_KEY` (and `GITHUB_TOKEN` for GitHub features)
in `backend/.env`, then:

```bash
docker compose up --build -d
```

- **Frontend:** http://localhost:8080
- **Backend API:** http://localhost:8000

The compose stack runs:

- **PostgreSQL 16** — relational persistence (chunks, repositories), with a
  healthcheck
- **Qdrant** — vector storage, with a healthcheck
- **backend** — FastAPI app; applies Alembic migrations on startup, embeds
  vectors via FastEmbed, and indexes into Qdrant
- **frontend** — nginx-served production build that reverse-proxies `/api`,
  `/repositories`, and `/health` to the backend

Named volumes persist Postgres data (`postgres_data`), Qdrant storage
(`qdrant_data`), and cloned repositories (`repo_data`).

## Roadmap

Completed milestones: project foundation → FastAPI backend → configuration
management → repository ingestion → retrieval & search → AI assistant (RAG
chat, agents, bug detection) → frontend foundation & screens → multi-agent
workflow → GitHub integration → production Docker deployment.

Upcoming: PR comment posting / auto-labels (write access), CI/CD pipeline,
usage analytics and observability.

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full breakdown.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — high-level architecture
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — milestones and upcoming work
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — version history (v0.1.0 → v0.3.0)
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — engineering decisions
