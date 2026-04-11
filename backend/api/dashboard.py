from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.task import Task, TaskStatus
from backend.models.agent import Agent
from backend.models.run_log import RunLog
from backend.models.artifact import Artifact
from backend.models.pull_request import PullRequest
from backend.llm.gateway import llm_gateway
from backend.ace.engine import ace_engine

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    agents = db.query(Agent).all()
    artifacts = db.query(Artifact).count()
    prs = db.query(PullRequest).count()
    logs = db.query(RunLog).count()

    status_counts = {}
    for t in tasks:
        s = t.status.value if hasattr(t.status, "value") else t.status
        status_counts[s] = status_counts.get(s, 0) + 1

    agent_summary = []
    for a in agents:
        task_count = db.query(Task).filter(Task.owner_agent_id == a.id).count()
        agent_summary.append({
            "id": a.id,
            "name": a.name,
            "role": a.role.value if hasattr(a.role, "value") else a.role,
            "status": a.status.value if hasattr(a.status, "value") else a.status,
            "task_count": task_count,
        })

    return {
        "task_counts": status_counts,
        "total_tasks": len(tasks),
        "agent_summary": agent_summary,
        "total_artifacts": artifacts,
        "total_prs": prs,
        "total_logs": logs,
        "llm_telemetry": llm_gateway.get_telemetry(),
        "ace_stats": ace_engine.get_stats(),
    }


@router.get("/activity-feed")
def get_activity_feed(limit: int = 50, db: Session = Depends(get_db)):
    logs = (
        db.query(RunLog)
        .order_by(RunLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    feed = []
    for log in logs:
        agent = db.query(Agent).filter(Agent.id == log.agent_id).first() if log.agent_id else None
        task = db.query(Task).filter(Task.id == log.task_id).first() if log.task_id else None
        feed.append({
            "id": log.id,
            "action": log.action,
            "agent_name": agent.name if agent else "System",
            "task_title": task.title if task else "N/A",
            "status": log.status.value if hasattr(log.status, "value") else log.status,
            "duration_ms": log.duration_ms,
            "timestamp": log.timestamp.isoformat() if log.timestamp else "",
        })
    return feed
