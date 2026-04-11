from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.pull_request import PullRequest, PRStatus
from backend.schemas.pull_request import PullRequestCreate, PullRequestUpdate, PullRequestResponse
from backend.git_manager.operations import pr_manager

router = APIRouter(prefix="/api/pull-requests", tags=["pull_requests"])


@router.get("/", response_model=list[PullRequestResponse])
def list_prs(status: str = None, db: Session = Depends(get_db)):
    query = db.query(PullRequest)
    if status:
        query = query.filter(PullRequest.status == status)
    return query.order_by(PullRequest.created_at.desc()).all()


@router.get("/{pr_id}", response_model=PullRequestResponse)
def get_pr(pr_id: int, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    return pr


@router.post("/{pr_id}/approve")
def approve_pr(pr_id: int, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    pr.status = PRStatus.APPROVED
    db.commit()
    return {"message": f"PR #{pr_id} approved"}


@router.post("/{pr_id}/merge")
def merge_pr(pr_id: int, db: Session = Depends(get_db)):
    pr = db.query(PullRequest).filter(PullRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=404, detail="Pull request not found")
    if pr.status != PRStatus.APPROVED:
        raise HTTPException(status_code=400, detail="PR must be approved before merging")
    pr.status = PRStatus.MERGED
    db.commit()
    return {"message": f"PR #{pr_id} merged"}
