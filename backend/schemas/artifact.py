from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ArtifactCreate(BaseModel):
    task_id: int
    agent_id: int
    artifact_type: str
    title: str = Field(..., max_length=500)
    content: str = ""
    file_path: Optional[str] = None
    extra_metadata: str = "{}"


class ArtifactResponse(BaseModel):
    id: int
    task_id: int
    agent_id: int
    artifact_type: str
    title: str
    content: str
    file_path: Optional[str]
    extra_metadata: str
    created_at: datetime

    class Config:
        from_attributes = True
