import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, JSON
from sqlalchemy.orm import relationship
from backend.database import Base


class AgentRole(str, enum.Enum):
    PROJECT_MANAGER = "project_manager"
    UX_DESIGNER = "ux_designer"
    FRONTEND_DEV = "frontend_dev"
    BACKEND_DEV = "backend_dev"
    FULLSTACK = "fullstack"
    RESEARCH = "research"
    DB_ENGINEER = "db_engineer"


class AgentStatus(str, enum.Enum):
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    role = Column(SAEnum(AgentRole), nullable=False)
    status = Column(SAEnum(AgentStatus), default=AgentStatus.IDLE)
    description = Column(Text, default="")
    capabilities = Column(JSON, default=list)
    model_profile = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    tasks = relationship("Task", back_populates="owner_agent")
    artifacts = relationship("Artifact", back_populates="agent")
    run_logs = relationship("RunLog", back_populates="agent")
