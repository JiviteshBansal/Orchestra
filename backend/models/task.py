import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    acceptance_criteria = Column(Text, default="")
    status = Column(SAEnum(TaskStatus), default=TaskStatus.BACKLOG, index=True)
    dependencies = Column(JSON, default=list)
    owner_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    reviewer_agent_ids = Column(JSON, default=list)
    risk_level = Column(SAEnum(RiskLevel), default=RiskLevel.MEDIUM)
    effort_estimate = Column(String(50), default="medium")
    project_name = Column(String(200), default="default")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner_agent = relationship("Agent", back_populates="tasks")
    artifacts = relationship("Artifact", back_populates="task", cascade="all, delete-orphan")
    run_logs = relationship("RunLog", back_populates="task", cascade="all, delete-orphan")
    pull_request = relationship("PullRequest", back_populates="task", uselist=False)
