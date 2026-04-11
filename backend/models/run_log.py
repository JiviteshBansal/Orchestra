import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class LogStatus(str, enum.Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class RunLog(Base):
    __tablename__ = "run_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    action = Column(String(200), nullable=False)
    input_data = Column(Text, default="{}")
    output_data = Column(Text, default="{}")
    status = Column(SAEnum(LogStatus), default=LogStatus.STARTED)
    duration_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="run_logs")
    agent = relationship("Agent", back_populates="run_logs")
