import json
import logging
import time
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from backend.agents.base import TaskInput, AgentOutput, ReviewFeedback
from backend.agents.registry import agent_registry
from backend.memory import memory_manager
from backend.tools.executor import tool_executor, ToolResult
from backend.git_manager.operations import git_manager, pr_manager
from backend.models.task import TaskStatus
from backend.models.run_log import LogStatus

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.registry = agent_registry
        self.memory = memory_manager
        self.tools = tool_executor
        self.git = git_manager
        self.prs = pr_manager
        self._active_workflows: dict[str, dict] = {}

    async def handle_request(self, request: str, project_name: str = "default", db: Session = None) -> dict:
        logger.info(f"[Orchestrator] New request: {request[:100]}...")
        workflow_id = f"wf_{int(time.time())}"
        self._active_workflows[workflow_id] = {
            "status": "planning",
            "request": request,
            "project_name": project_name,
            "tasks": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        pm = self.registry.get_agent("project_manager")
        if not pm:
            return {"error": "Project Manager agent not available", "workflow_id": workflow_id}

        plan_input = TaskInput(
            task_id=0,
            title="Project Planning",
            description=request,
            acceptance_criteria="Create a comprehensive task breakdown",
            project_name=project_name,
        )

        plan_output = await pm.execute(plan_input)
        self.memory.store_task_context(0, f"Project plan: {plan_output.solution_artifact}", {
            "type": "plan",
            "project": project_name,
        })

        tasks = self._parse_task_plan(plan_output.solution_artifact)
        if db:
            db_tasks = self._create_db_tasks(db, tasks, project_name)
            self._active_workflows[workflow_id]["tasks"] = [t.id for t in db_tasks]

        self._active_workflows[workflow_id]["status"] = "planned"
        self._active_workflows[workflow_id]["plan"] = plan_output.to_dict()
        self._active_workflows[workflow_id]["task_count"] = len(tasks)

        return {
            "workflow_id": workflow_id,
            "status": "planned",
            "task_count": len(tasks),
            "tasks": tasks,
            "plan": plan_output.reasoning_summary,
        }

    async def execute_task(self, task_id: int, db: Session = None) -> dict:
        from backend.models.task import Task
        from backend.models.agent import Agent
        from backend.models.artifact import Artifact
        from backend.models.run_log import RunLog

        if not db:
            return {"error": "Database session required"}

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": f"Task {task_id} not found"}

        if not task.owner_agent_id:
            return {"error": f"Task {task_id} has no assigned agent"}

        agent_record = db.query(Agent).filter(Agent.id == task.owner_agent_id).first()
        if not agent_record:
            return {"error": f"Agent {task.owner_agent_id} not found"}

        agent = self.registry.get_agent(agent_record.role.value if hasattr(agent_record.role, 'value') else agent_record.role)
        if not agent:
            return {"error": f"Agent role {agent_record.role} not registered"}

        task.status = TaskStatus.IN_PROGRESS
        agent_record.status = "busy"
        db.commit()

        log = RunLog(
            task_id=task.id,
            agent_id=agent_record.id,
            action="execute_task",
            input_data=json.dumps({"title": task.title, "description": task.description}),
            status=LogStatus.STARTED,
        )
        db.add(log)
        db.commit()

        start_time = time.time()
        task_input = TaskInput(
            task_id=task.id,
            title=task.title,
            description=task.description,
            acceptance_criteria=task.acceptance_criteria or "",
            project_name=task.project_name,
        )

        output = await agent.execute(task_input)

        duration_ms = (time.time() - start_time) * 1000
        log.status = LogStatus.COMPLETED if output.status == "completed" else LogStatus.FAILED
        log.output_data = json.dumps(output.to_dict())
        log.duration_ms = duration_ms
        if output.error:
            log.error_message = output.error

        artifact = Artifact(
            task_id=task.id,
            agent_id=agent_record.id,
            artifact_type="code",
            title=f"Output: {task.title}",
            content=output.solution_artifact,
        )
        db.add(artifact)

        self.memory.store_task_context(task.id, output.solution_artifact, {
            "type": "task_output",
            "agent": agent.name,
        })

        task.status = TaskStatus.REVIEW
        agent_record.status = "idle"
        db.commit()

        return {
            "task_id": task.id,
            "status": "review",
            "output": output.to_dict(),
            "duration_ms": duration_ms,
        }

    async def review_task(self, task_id: int, db: Session = None) -> dict:
        from backend.models.task import Task
        from backend.models.agent import Agent
        from backend.models.artifact import Artifact
        from backend.models.run_log import RunLog

        if not db:
            return {"error": "Database session required"}

        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"error": f"Task {task_id} not found"}

        artifacts = db.query(Artifact).filter(Artifact.task_id == task_id).all()
        if not artifacts:
            return {"error": f"No artifacts to review for task {task_id}"}

        owner_agent = db.query(Agent).filter(Agent.id == task.owner_agent_id).first()
        if not owner_agent:
            return {"error": "Owner agent not found"}

        owner_role = owner_agent.role.value if hasattr(owner_agent.role, 'value') else owner_agent.role
        reviewer = self.registry.get_reviewer_for(owner_role)
        if not reviewer:
            return {"error": f"No reviewer found for role {owner_role}"}

        latest_artifact = artifacts[-1]
        task_input = TaskInput(
            task_id=task.id,
            title=task.title,
            description=task.description,
            acceptance_criteria=task.acceptance_criteria or "",
        )
        agent_output = AgentOutput(
            solution_artifact=latest_artifact.content,
            reasoning_summary=f"Output from {owner_agent.name}",
        )

        review = await reviewer.review(task_input, agent_output)

        review_artifact = Artifact(
            task_id=task.id,
            agent_id=reviewer.agent_id,
            artifact_type="review",
            title=f"Review: {task.title}",
            content=json.dumps(review.to_dict()),
        )
        db.add(review_artifact)

        log = RunLog(
            task_id=task.id,
            agent_id=reviewer.agent_id,
            action="review_task",
            input_data=json.dumps({"task_title": task.title}),
            output_data=json.dumps(review.to_dict()),
            status=LogStatus.COMPLETED,
        )
        db.add(log)

        if review.approved:
            task.status = TaskStatus.DONE
            branch_name = f"task-{task.id}-{task.title.lower().replace(' ', '-')[:30]}"
            self.git.create_branch(branch_name)
            for art in artifacts:
                if art.content and art.artifact_type != "review":
                    filename = f"task_{task.id}_{art.title.replace(' ', '_')[:50]}.txt"
                    self.tools.execute_tool("write_file", art.agent_id, {
                        "path": f"{task.project_name}/{filename}",
                        "content": art.content,
                    })
                    self.git.commit_files(
                        [f"{task.project_name}/{filename}"],
                        f"[Task #{task.id}] {task.title}"
                    )

            pr = self.prs.create_pr(
                task_id=task.id,
                branch_name=branch_name,
                title=f"[Task #{task.id}] {task.title}",
                what_changed=latest_artifact.content[:500],
                why_changed=task.description[:500],
                how_changed=f"Implemented by {owner_agent.name}",
                test_plan="\n".join(
                    item.get("item", "") for item in agent_output.validation_checklist
                ),
            )

            self.memory.store_task_context(task.id, json.dumps(review.to_dict()), {
                "type": "review",
                "approved": True,
            })
        else:
            task.status = TaskStatus.IN_PROGRESS

        db.commit()

        return {
            "task_id": task.id,
            "approved": review.approved,
            "status": task.status.value,
            "review": review.to_dict(),
        }

    def _parse_task_plan(self, plan_text: str) -> list[dict]:
        try:
            start = plan_text.find("[")
            end = plan_text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(plan_text[start:end])
        except (json.JSONDecodeError, ValueError):
            pass

        tasks = []
        lines = plan_text.strip().split("\n")
        current_task = None
        for line in lines:
            line = line.strip()
            if line.startswith(("#", "-", "*", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                if current_task:
                    tasks.append(current_task)
                title = line.lstrip("#-*0123456789. ").strip()
                if title:
                    current_task = {
                        "title": title,
                        "description": title,
                        "acceptance_criteria": "Task completed successfully",
                        "assigned_role": "fullstack",
                        "risk_level": "medium",
                        "effort_estimate": "medium",
                        "dependencies": [],
                        "reviewer_role": "backend_dev",
                    }
            elif current_task and line:
                current_task["description"] += f" {line}"

        if current_task:
            tasks.append(current_task)

        if not tasks:
            tasks.append({
                "title": "Implement request",
                "description": plan_text[:500],
                "acceptance_criteria": "Implementation complete",
                "assigned_role": "fullstack",
                "risk_level": "medium",
                "effort_estimate": "medium",
                "dependencies": [],
                "reviewer_role": "backend_dev",
            })

        return tasks

    def _create_db_tasks(self, db: Session, tasks: list[dict], project_name: str) -> list:
        from backend.models.task import Task
        from backend.models.agent import Agent

        db_tasks = []
        for t in tasks:
            role = t.get("assigned_role", "fullstack")
            agent = db.query(Agent).filter(Agent.role == role).first()

            task = Task(
                title=t.get("title", "Untitled"),
                description=t.get("description", ""),
                acceptance_criteria=t.get("acceptance_criteria", ""),
                status=TaskStatus.BACKLOG,
                owner_agent_id=agent.id if agent else None,
                risk_level=t.get("risk_level", "medium"),
                effort_estimate=t.get("effort_estimate", "medium"),
                project_name=project_name,
            )
            db.add(task)
            db_tasks.append(task)

        db.commit()
        for task in db_tasks:
            db.refresh(task)
        return db_tasks

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        return self._active_workflows.get(workflow_id)

    def list_workflows(self) -> list[dict]:
        return [
            {"id": k, "status": v["status"], "task_count": v.get("task_count", 0)}
            for k, v in self._active_workflows.items()
        ]


orchestrator = Orchestrator()
