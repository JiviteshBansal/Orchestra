import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class PRStatus(str, enum.Enum):
    OPEN = "open"
    APPROVED = "approved"
    MERGED = "merged"
    REJECTED = "rejected"


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, unique=True)
    branch_name = Column(String(200), nullable=False)
    title = Column(String(500), nullable=False)
    what_changed = Column(Text, default="")
    why_changed = Column(Text, default="")
    how_changed = Column(Text, default="")
    test_plan = Column(Text, default="")
    status = Column(SAEnum(PRStatus), default=PRStatus.OPEN)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("Task", back_populates="pull_request")
