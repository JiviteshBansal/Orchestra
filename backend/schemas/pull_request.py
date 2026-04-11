from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PullRequestCreate(BaseModel):
    task_id: int
    branch_name: str
    title: str = Field(..., max_length=500)
    what_changed: str = ""
    why_changed: str = ""
    how_changed: str = ""
    test_plan: str = ""


class PullRequestUpdate(BaseModel):
    status: Optional[str] = None
    what_changed: Optional[str] = None
    why_changed: Optional[str] = None
    how_changed: Optional[str] = None
    test_plan: Optional[str] = None


class PullRequestResponse(BaseModel):
    id: int
    task_id: int
    branch_name: str
    title: str
    what_changed: str
    why_changed: str
    how_changed: str
    test_plan: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
