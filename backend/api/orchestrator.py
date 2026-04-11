from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db
from backend.orchestrator.core import orchestrator

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])


class ProjectRequest(BaseModel):
    description: str
    project_name: str = "default"


class ExecuteTaskRequest(BaseModel):
    task_id: int


@router.post("/request")
async def submit_request(req: ProjectRequest, db: Session = Depends(get_db)):
    result = await orchestrator.handle_request(
        request=req.description,
        project_name=req.project_name,
        db=db,
    )
    return result


@router.post("/execute")
async def execute_task(req: ExecuteTaskRequest, db: Session = Depends(get_db)):
    result = await orchestrator.execute_task(task_id=req.task_id, db=db)
    return result


@router.post("/review")
async def review_task(req: ExecuteTaskRequest, db: Session = Depends(get_db)):
    result = await orchestrator.review_task(task_id=req.task_id, db=db)
    return result


@router.get("/workflows")
def list_workflows():
    return orchestrator.list_workflows()


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str):
    wf = orchestrator.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf
