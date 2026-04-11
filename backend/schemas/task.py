from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str
    acceptance_criteria: str = ""
    dependencies: list[int] = []
    owner_agent_id: Optional[int] = None
    reviewer_agent_ids: list[int] = []
    risk_level: str = "medium"
    effort_estimate: str = "medium"
    project_name: str = "default"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    status: Optional[str] = None
    dependencies: Optional[list[int]] = None
    owner_agent_id: Optional[int] = None
    reviewer_agent_ids: Optional[list[int]] = None
    risk_level: Optional[str] = None
    effort_estimate: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    acceptance_criteria: str
    status: str
    dependencies: list[int]
    owner_agent_id: Optional[int]
    reviewer_agent_ids: list[int]
    risk_level: str
    effort_estimate: str
    project_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskBoardResponse(BaseModel):
    backlog: list[TaskResponse] = []
    in_progress: list[TaskResponse] = []
    review: list[TaskResponse] = []
    done: list[TaskResponse] = []
