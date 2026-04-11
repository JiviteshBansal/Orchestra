# 🎼 Orchestra AI

A **local-first multi-agent AI software development system** where specialized AI agents collaboratively plan, build, review, and deliver software projects.

## Architecture

```
User Request → Orchestrator → PM Agent (plans) → Specialized Agents (execute) → Review → Git PR → Done
```

### Agents
| Agent | Role | Responsibilities |
|-------|------|-----------------|
| 📋 Project Manager | Planning | Task breakdown, estimation, coordination |
| 🎨 UX Designer | Design | Wireframes, user flows, design specs |
| ⚛️ Frontend Dev | Frontend | React + TypeScript components |
| ⚙️ Backend Dev | Backend | Python + FastAPI APIs |
| 🔧 Full Stack | Integration | Cross-stack features |
| 🔬 Researcher | Analysis | Technical research, architecture |
| 🗄️ DB Engineer | Database | Schema design, migrations |

### Key Features
- **Hierarchical orchestration** — all agent communication goes through the Orchestrator
- **Mandatory review cycle** — every task is reviewed by a peer agent before completion
- **Git + PR integration** — branch per task, auto-generated PRs with what/why/how
- **FAISS vector memory** — long-term retrieval of design decisions and past outputs
- **ACE Learning System** — learns from approved tasks, generates playbooks
- **Docker sandbox** — safe terminal command execution
- **LLM Gateway** — LM Studio (local CodeLlama) with remote fallback support

## Tech Stack
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy + SQLite
- **Frontend**: React 18 + TypeScript + Vite
- **LLM**: LM Studio (CodeLlama-7B-Instruct) at `127.0.0.1:1234`
- **Vector Store**: FAISS + sentence-transformers
- **Sandbox**: Docker

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- LM Studio running CodeLlama-7B-Instruct on port 1234
- Docker (optional, for sandboxed execution)

### Setup
```bash
chmod +x setup.sh
./setup.sh
```

### Run
```bash
# Terminal 1 — Backend
PYTHONPATH=. python3 -m uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend && npm run dev
```

### Access
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orchestrator/request` | Submit a project request |
| POST | `/api/orchestrator/execute` | Execute a task |
| POST | `/api/orchestrator/review` | Review a task |
| GET | `/api/tasks/board` | Get Kanban board |
| GET | `/api/agents/` | List all agents |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| GET | `/api/dashboard/activity-feed` | Agent activity feed |
| GET | `/api/artifacts/` | List artifacts |
| GET | `/api/pull-requests/` | List PRs |
| POST | `/api/pull-requests/{id}/approve` | Approve a PR |

## Workflow

1. **Submit** a project request through the dashboard
2. **PM Agent** breaks it into tasks with dependencies
3. Tasks appear on the **Kanban board** (Backlog)
4. **Execute** tasks — Orchestrator assigns to the right agent
5. Agent produces artifacts, task moves to **Review**
6. **Peer review** by another agent — approve or revise
7. Approved tasks get **Git commits** and **PR creation**
8. Track everything in the **activity feed** and **artifact viewer**

## Configuration

Edit `.env` in the project root:
```env
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=codellama-7b-instruct
OPENAI_API_KEY=      # optional remote fallback
ANTHROPIC_API_KEY=   # optional remote fallback
```

## License
MIT
