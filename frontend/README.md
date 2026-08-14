# CodePilot AI — Frontend

React + Vite + TypeScript web app for CodePilot, an AI software engineering
agent. Clone a GitHub repository, then chat, search, run agents, detect bugs,
and review PRs/issues against it — all from a single workspace.

## Stack

- React 19, TypeScript, Vite
- Tailwind CSS 4 + shadcn/ui (Radix primitives) + lucide-react
- Vitest + Testing Library for tests, oxlint for linting
- Served in production by nginx

## Getting started

```bash
npm install
cp .env.example .env   # VITE_API_URL, defaults to http://localhost:8000
npm run dev            # http://localhost:5173
```

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Type-check (`tsc -b`) and build (`vite build`) |
| `npm run preview` | Preview the production build |
| `npm run lint` | Lint with oxlint |
| `npm run test` | Run tests with Vitest |

## Environment variables

| Variable | Description |
| --- | --- |
| `VITE_API_URL` | Backend base URL (e.g. `http://localhost:8000`). In production builds it falls back to the hosted backend if unset |

## Structure

```
src/
├── components/
│   ├── agent-tab.tsx          # Single/multi-agent runner + tool traces
│   ├── bug-detection-tab.tsx  # Bug findings & sources
│   ├── chat-tab.tsx           # RAG chat with streaming + cited sources
│   ├── github-tab.tsx         # PR listing/review + issue listing/triage
│   ├── search-tab.tsx         # Semantic code search results
│   ├── repository-sidebar.tsx # Repo list, clone form, clone progress
│   ├── workspace-header.tsx   # App header + tab navigation
│   └── ui/                    # shadcn/ui primitives (button, card, tabs, …)
├── context/                   # Workspace + theme providers
├── hooks/                     # use-async-submit, use-repository-reset
├── lib/                       # Typed ApiClient, error formatting, utils
├── types/                     # API types mirroring backend schemas
├── test/                      # Vitest setup
└── App.tsx                    # Workspace shell (sidebar + tab layout)
```

The UI is organized as a workspace: a repository sidebar on the left (clone a
repo or pick an indexed one) and five tabs on the right — Chat, Search, Agent,
Bug Detection, and GitHub.

## API client

`src/lib/api.ts` provides a typed `ApiClient` covering every backend endpoint:
repository clone/status/cancel/reindex/delete, search, chat (including SSE
`streamChat` with `onDelta`/`onSources`/`onDone` callbacks), agent, bugs, PRs,
and issues. It handles timeouts, retries on 502/503, and friendly error
parsing. Types live in `src/types/api.ts`.

## Tests

```bash
npm run test
```

Tests cover the chat composer, chat tab, repository sidebar, and API/error
formatting utilities.

## Docker

`Dockerfile` builds the app with `npm ci && npm run build` and serves the
`dist/` output with nginx. `nginx.conf` proxies `/api`, `/repositories`, and
`/health` to the backend service. Build it from the repo root with:

```bash
docker compose up --build -d
```

The frontend is served at http://localhost:8080.
