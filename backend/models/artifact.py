import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class ArtifactType(str, enum.Enum):
    CODE = "code"
    DOCUMENT = "document"
    DESIGN = "design"
    TEST = "test"
    CONFIG = "config"
    REVIEW = "review"


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    artifact_type = Column(SAEnum(ArtifactType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, default="")
    file_path = Column(String(1000), nullable=True)
    extra_metadata = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="artifacts")
    agent = relationship("Agent", back_populates="artifacts")
