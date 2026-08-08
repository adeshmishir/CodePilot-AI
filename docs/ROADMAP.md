# CodePilot AI Roadmap

## ✅ Milestone 1 - Project Foundation

- Repository created
- Virtual environment setup
- Backend folder structure
- Frontend folder structure
- Documentation initialized

---

## ✅ Milestone 2 - FastAPI Backend

- FastAPI application
- APIRouter
- Health endpoint
- Swagger documentation

---

## ✅ Milestone 3 - Configuration Management

- Environment variables
- Settings class
- App configuration

---

## ✅ Milestone 4 - Repository Ingestion

- GitHub repository cloning service
- Repository API endpoint (`POST /repositories/clone`)
- Repository listing endpoint (`GET /repositories`)
- PostgreSQL persistence with Alembic migrations
- Tree-sitter AST parsing and symbol extraction
- Multi-language parsing support
- Semantic code chunk generation
- Repository indexing pipeline

---

## ✅ Milestone 5 - Retrieval & Search

- Code embeddings and vector indexing (Qdrant)
- Semantic code retrieval
- Semantic code search API (`POST /api/repositories/{id}/search`)

---

## ✅ Milestone 6 - AI Assistant

- Repository-aware RAG (chat endpoint)
- Agent planning and tool execution layer
- Bug detection workflow (`POST /api/repositories/{id}/bugs`)

---

## ✅ Milestone 7 - Frontend Foundation

- Vite + React + TypeScript scaffold
- Tailwind CSS configuration
- shadcn/ui primitives (button, card, input, textarea, badge, tabs, label)
- Shared TypeScript types mirroring backend schemas
- Typed API client
- Application shell (repository sidebar + clone form)

---

## ✅ Milestone 8 - Frontend Screens

- Chat tab
- Semantic Search tab
- Agent tab
- Bug Detection tab

---

## Upcoming

- Multi-Agent Workflow
- GitHub Integration (PR review / issue triage)
- Production deployment
