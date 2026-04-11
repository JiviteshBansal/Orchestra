from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    name: str = Field(..., max_length=200)
    role: str
    description: str = ""
    capabilities: list[str] = []
    model_profile: dict = {}


class AgentUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[list[str]] = None
    model_profile: Optional[dict] = None


class AgentResponse(BaseModel):
    id: int
    name: str
    role: str
    status: str
    description: str
    capabilities: list[str]
    model_profile: dict
    created_at: datetime

    class Config:
        from_attributes = True
