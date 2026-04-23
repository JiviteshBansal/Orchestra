from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db, SessionLocal
from backend.orchestrator.core import orchestrator

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


class ProjectRequest(BaseModel):
    description: str
    project_name: str = "default"


class ExecuteTaskRequest(BaseModel):
    task_id: int


# Store background workflow results
_background_results: dict[str, dict] = {}


async def _run_pipeline(description: str, project_name: str, workflow_id: str):
    """Run the full pipeline in the background."""
    db = SessionLocal()
    try:
        result = await orchestrator.handle_request(
            request=description,
            project_name=project_name,
            db=db,
        )
        _background_results[workflow_id] = result
    except Exception as e:
        _background_results[workflow_id] = {"error": str(e), "workflow_id": workflow_id}
    finally:
        db.close()


@router.post("/request")
async def submit_request(req: ProjectRequest, db: Session = Depends(get_db)):
    """Submit a project request. Runs plan + execute + review pipeline."""
    result = await orchestrator.handle_request(
        request=req.description,
        project_name=req.project_name,
        db=db,
    )
    return result


@router.post("/execute")
async def execute_task(req: ExecuteTaskRequest, db: Session = Depends(get_db)):
    """Manually execute a single task."""
    result = await orchestrator.execute_task(task_id=req.task_id, db=db)
    return result


@router.post("/review")
async def review_task(req: ExecuteTaskRequest, db: Session = Depends(get_db)):
    """Manually review a single task."""
    result = await orchestrator.review_task(task_id=req.task_id, db=db)
    return result


@router.get("/workflows")
def list_workflows():
    """List all workflows with their status."""
    return orchestrator.list_workflows()


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    """Get detailed workflow status including progress log."""
    wf = orchestrator.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.get("/workflows/{workflow_id}/progress")
def get_workflow_progress(workflow_id: str):
    """Get just the progress log for a workflow (for polling)."""
    wf = orchestrator.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow_id,
        "status": wf.get("status", "unknown"),
        "progress": wf.get("progress", []),
        "task_count": wf.get("task_count", 0),
    }
