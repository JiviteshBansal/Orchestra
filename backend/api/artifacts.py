from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.artifact import Artifact
from backend.schemas.artifact import ArtifactResponse

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/", response_model=list[ArtifactResponse])
def list_artifacts(task_id: int = None, agent_id: int = None, db: Session = Depends(get_db)):
    query = db.query(Artifact)
    if task_id:
        query = query.filter(Artifact.task_id == task_id)
    if agent_id:
        query = query.filter(Artifact.agent_id == agent_id)
    return query.order_by(Artifact.created_at.desc()).all()


@router.get("/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.query(Artifact).filter(Artifact.id == artifact_id).first()
    if not artifact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact
