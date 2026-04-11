import logging
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings, BASE_DIR
from backend.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = BASE_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME}...")
    init_db()
    logger.info("Database initialized")

    from sqlalchemy.orm import Session
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        from backend.models.agent import Agent
        if db.query(Agent).count() == 0:
            from backend.api.agents import seed_agents
            seed_agents(db)
            logger.info("Default agents seeded")
    finally:
        db.close()

    yield
    logger.info(f"{settings.APP_NAME} shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Local-first multi-agent AI software development system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.api.tasks import router as tasks_router
from backend.api.agents import router as agents_router
from backend.api.orchestrator import router as orchestrator_router
from backend.api.artifacts import router as artifacts_router
from backend.api.pull_requests import router as pr_router
from backend.api.dashboard import router as dashboard_router

app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(orchestrator_router)
app.include_router(artifacts_router)
app.include_router(pr_router)
app.include_router(dashboard_router)


@app.get("/health")
def health():
    return {"status": "healthy"}


# Serve React frontend static files in Docker
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Serve index.html for all non-API, non-asset routes (SPA routing)
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    def root():
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
        }

