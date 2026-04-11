from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.task import Task, TaskStatus
from backend.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskBoardResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(
        title=task.title,
        description=task.description,
        acceptance_criteria=task.acceptance_criteria,
        dependencies=task.dependencies,
        owner_agent_id=task.owner_agent_id,
        reviewer_agent_ids=task.reviewer_agent_ids,
        risk_level=task.risk_level,
        effort_estimate=task.effort_estimate,
        project_name=task.project_name,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    status: str = None,
    project: str = None,
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if project:
        query = query.filter(Task.project_name == project)
    return query.order_by(Task.created_at.desc()).all()


@router.get("/board", response_model=TaskBoardResponse)
def get_board(project: str = None, db: Session = Depends(get_db)):
    query = db.query(Task)
    if project:
        query = query.filter(Task.project_name == project)
    tasks = query.all()

    board = TaskBoardResponse()
    for t in tasks:
        status = t.status.value if hasattr(t.status, "value") else t.status
        resp = TaskResponse.model_validate(t)
        if status == "backlog":
            board.backlog.append(resp)
        elif status == "in_progress":
            board.in_progress.append(resp)
        elif status == "review":
            board.review.append(resp)
        elif status == "done":
            board.done.append(resp)
    return board


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, update: TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}
