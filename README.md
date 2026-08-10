# CodePilot-AI

An AI software engineering agent: clone a GitHub repo, index its code, and
chat, search, run agents, detect bugs, and triage GitHub PRs/issues against it.

## Stack

- Frontend: React + Vite + TypeScript + Tailwind + shadcn/ui
- Backend: FastAPI + SQLAlchemy + PostgreSQL + Qdrant + tree-sitter + Groq
- AI: RAG chat, single/multi-agent execution, bug detection, PR review, issue triage

## Local development

Backend (from `backend/`):

```
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Frontend (from `frontend/`):

```
npm run dev
```

### Environment

Copy `backend/.env.example` to `backend/.env` and set:

- `GROQ_API_KEY` — required for every AI feature (chat, agent, bugs, triage, review)
- `GITHUB_TOKEN` — required for GitHub features (PR review, issue triage); a
  classic personal access token with `repo` scope (or `public_repo` for public repos)
- `DATABASE_URL` — PostgreSQL connection string
- `QDRANT_URL` — Qdrant location; leave as `:memory:` for local in-memory vectors,
  or point at a running Qdrant instance (e.g. `http://localhost:6333`)
- `CORS_ORIGINS` — JSON list of allowed browser origins
  (e.g. `["http://localhost:8080"]`)

## API

Interactive docs: `http://127.0.0.1:8000/docs`

- `POST /repositories/clone` — clone and index a GitHub repo
- `GET /repositories` — list indexed repositories
- `POST /api/repositories/{id}/search` — semantic code search
- `POST /api/repositories/{id}/chat` — repository-aware RAG chat
- `POST /api/repositories/{id}/agent` — single or multi-agent execution
- `POST /api/repositories/{id}/bugs` — bug detection
- `GET /api/repositories/{id}/github/prs` — open pull requests
- `POST /api/repositories/{id}/github/prs/{n}/review` — review a pull request
- `GET /api/repositories/{id}/github/issues` — open issues
- `POST /api/repositories/{id}/github/issues/triage` — triage open issues

## Production deployment (Docker)

Requires Docker. Set `GROQ_API_KEY` and `GITHUB_TOKEN` in `backend/.env`, then:

```
docker compose up --build -d
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:8000

The compose stack runs PostgreSQL, Qdrant, the FastAPI backend (applies Alembic
migrations on startup), and the nginx-served frontend build.
