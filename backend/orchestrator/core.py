import json
import re
import logging
import time
import asyncio
from typing import Optional
from datetime import datetime

from sqlalchemy.orm import Session

from backend.agents.base import TaskInput, AgentOutput, ReviewFeedback, extract_files_from_output
from backend.agents.registry import agent_registry
from backend.memory import memory_manager
from backend.tools.executor import tool_executor, ToolResult
from backend.git_manager.operations import git_manager, pr_manager
from backend.models.task import TaskStatus, RiskLevel
from backend.models.run_log import LogStatus
from backend.config import settings

logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self):
        self.registry = agent_registry
        self.memory = memory_manager
        self.tools = tool_executor
        self.git = git_manager
        self.prs = pr_manager
        self._active_workflows: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Main entry point: handle_request (plan + auto-execute if enabled)
    # ------------------------------------------------------------------

    async def handle_request(self, request: str, project_name: str = "default", db: Session = None) -> dict:
        logger.info(f"[Orchestrator] New request: {request[:100]}...")
        workflow_id = f"wf_{int(time.time())}"
        self._active_workflows[workflow_id] = {
            "status": "planning",
            "request": request,
            "project_name": project_name,
            "tasks": [],
            "results": [],
            "progress": [],
            "created_at": datetime.utcnow().isoformat(),
        }

        self._log_progress(workflow_id, "planning", "Project Manager is analyzing request...")

        # --- PHASE 1: Planning ---
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

        tasks = self._parse_task_plan(plan_output.solution_artifact, request)
        self._log_progress(workflow_id, "planned", f"Created {len(tasks)} tasks from plan")

        db_tasks = []
        if db:
            db_tasks = self._create_db_tasks(db, tasks, project_name)
            self._active_workflows[workflow_id]["tasks"] = [t.id for t in db_tasks]

        self._active_workflows[workflow_id]["status"] = "planned"
        self._active_workflows[workflow_id]["plan"] = plan_output.to_dict()
        self._active_workflows[workflow_id]["task_count"] = len(tasks)

        # --- PHASE 2: Auto-execute if enabled ---
        if settings.AUTO_EXECUTE and db and db_tasks:
            self._active_workflows[workflow_id]["status"] = "executing"
            self._log_progress(workflow_id, "executing", "Starting auto-execution pipeline...")

            for i, db_task in enumerate(db_tasks):
                task_label = f"[{i+1}/{len(db_tasks)}] {db_task.title}"
                self._log_progress(workflow_id, "executing", f"Executing: {task_label}")

                try:
                    exec_result = await self.execute_task(db_task.id, db=db)
                    self._active_workflows[workflow_id]["results"].append({
                        "task_id": db_task.id,
                        "phase": "execute",
                        "result": exec_result,
                    })

                    if exec_result.get("error"):
                        self._log_progress(workflow_id, "executing",
                                           f"⚠ Execution failed for {task_label}: {exec_result['error']}")
                        continue

                    # Auto-review
                    self._log_progress(workflow_id, "reviewing", f"Reviewing: {task_label}")
                    review_result = await self.review_task(db_task.id, db=db)
                    self._active_workflows[workflow_id]["results"].append({
                        "task_id": db_task.id,
                        "phase": "review",
                        "result": review_result,
                    })

                    if review_result.get("approved"):
                        self._log_progress(workflow_id, "executing",
                                           f"✓ {task_label} — approved")
                    else:
                        self._log_progress(workflow_id, "executing",
                                           f"↻ {task_label} — needs revision, re-executing...")
                        # One retry: re-execute and auto-approve
                        exec2 = await self.execute_task(db_task.id, db=db)
                        if not exec2.get("error"):
                            review2 = await self.review_task(db_task.id, db=db)
                            self._active_workflows[workflow_id]["results"].append({
                                "task_id": db_task.id,
                                "phase": "retry",
                                "result": review2,
                            })

                except Exception as e:
                    logger.error(f"Pipeline error on task {db_task.id}: {e}")
                    self._log_progress(workflow_id, "error", f"Error on {task_label}: {str(e)}")

            self._active_workflows[workflow_id]["status"] = "completed"
            self._log_progress(workflow_id, "completed", "Pipeline finished! All tasks processed.")

        return {
            "workflow_id": workflow_id,
            "status": self._active_workflows[workflow_id]["status"],
            "task_count": len(tasks),
            "tasks": tasks,
            "plan": plan_output.reasoning_summary,
            "progress": self._active_workflows[workflow_id]["progress"],
        }

    # ------------------------------------------------------------------
    # Execute a single task
    # ------------------------------------------------------------------

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

        # Store full artifact
        artifact = Artifact(
            task_id=task.id,
            agent_id=agent_record.id,
            artifact_type="code",
            title=f"Output: {task.title}",
            content=output.solution_artifact,
        )
        db.add(artifact)

        # Store individual file artifacts
        for att in output.attachments:
            file_artifact = Artifact(
                task_id=task.id,
                agent_id=agent_record.id,
                artifact_type=att.file_type,
                title=att.filename,
                content=att.content,
                file_path=att.filename,
            )
            db.add(file_artifact)

        self.memory.store_task_context(task.id, output.solution_artifact, {
            "type": "task_output",
            "agent": agent.name,
            "files": [a.filename for a in output.attachments],
        })

        task.status = TaskStatus.REVIEW
        agent_record.status = "idle"
        db.commit()

        return {
            "task_id": task.id,
            "status": "review",
            "output": output.to_dict(),
            "duration_ms": duration_ms,
            "files_produced": len(output.attachments),
        }

    # ------------------------------------------------------------------
    # Review a task (with real file writing)
    # ------------------------------------------------------------------

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

        # Build output with attachments from stored artifacts
        file_artifacts = [a for a in artifacts if a.file_path]
        attachments_for_review = []
        from backend.agents.base import Attachment
        for fa in file_artifacts:
            attachments_for_review.append(Attachment(
                filename=fa.file_path,
                content=fa.content,
                file_type=fa.artifact_type,
            ))

        agent_output = AgentOutput(
            solution_artifact=latest_artifact.content,
            reasoning_summary=f"Output from {owner_agent.name}",
            attachments=attachments_for_review,
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

            # Write REAL files to the project directory
            project_dir = task.project_name or "default"
            written_files = []

            # Write individual file artifacts as real code files
            for fa in file_artifacts:
                file_path = f"{project_dir}/{fa.file_path}"
                self.tools.execute_tool("write_file", fa.agent_id, {
                    "path": file_path,
                    "content": fa.content,
                })
                written_files.append(file_path)
                logger.info(f"Wrote file: {file_path}")

            # If no individual files, try extracting from the main artifact
            if not file_artifacts:
                main_artifacts = [a for a in artifacts if a.artifact_type != "review" and a.content]
                for art in main_artifacts:
                    extracted = extract_files_from_output(art.content)
                    if extracted:
                        for fname, fcontent, ftype in extracted:
                            file_path = f"{project_dir}/{fname}"
                            self.tools.execute_tool("write_file", art.agent_id, {
                                "path": file_path,
                                "content": fcontent,
                            })
                            written_files.append(file_path)
                    else:
                        # Last resort: write as a properly-named file based on agent role
                        ext = self._get_ext_for_role(owner_role)
                        fname = f"{project_dir}/task_{task.id}_{task.title.lower().replace(' ', '_')[:30]}{ext}"
                        self.tools.execute_tool("write_file", art.agent_id, {
                            "path": fname,
                            "content": art.content,
                        })
                        written_files.append(fname)

            # Git operations
            try:
                branch_name = f"task-{task.id}-{task.title.lower().replace(' ', '-')[:30]}"
                self.git.create_branch(branch_name)
                if written_files:
                    self.git.commit_files(
                        written_files,
                        f"[Task #{task.id}] {task.title}"
                    )

                pr = self.prs.create_pr(
                    task_id=task.id,
                    branch_name=branch_name,
                    title=f"[Task #{task.id}] {task.title}",
                    what_changed=f"Files: {', '.join(written_files[:10])}",
                    why_changed=task.description[:500],
                    how_changed=f"Implemented by {owner_agent.name}",
                    test_plan="\n".join(
                        item.get("item", "") for item in agent_output.validation_checklist
                    ),
                )
            except Exception as e:
                logger.warning(f"Git/PR operations failed (non-fatal): {e}")

            self.memory.store_task_context(task.id, json.dumps(review.to_dict()), {
                "type": "review",
                "approved": True,
                "files_written": written_files,
            })
        else:
            task.status = TaskStatus.IN_PROGRESS

        db.commit()

        return {
            "task_id": task.id,
            "approved": review.approved,
            "status": task.status.value,
            "review": review.to_dict(),
            "files_written": written_files if review.approved else [],
        }

    # ------------------------------------------------------------------
    # Robust task plan parser
    # ------------------------------------------------------------------

    def _parse_task_plan(self, plan_text: str, original_request: str = "") -> list[dict]:
        """Parse tasks from PM agent output. Handles JSON, markdown, numbered lists."""

        # Strategy 1: JSON in code fences
        json_fence = re.search(r"```(?:json)?\s*\n(\[.*?\])\s*\n```", plan_text, re.DOTALL)
        if json_fence:
            try:
                tasks = json.loads(json_fence.group(1))
                if isinstance(tasks, list) and len(tasks) > 0:
                    return [self._normalize_task(t) for t in tasks]
            except (json.JSONDecodeError, ValueError):
                pass

        # Strategy 2: Raw JSON array
        try:
            start = plan_text.find("[")
            end = plan_text.rfind("]") + 1
            if start >= 0 and end > start:
                candidate = plan_text[start:end]
                tasks = json.loads(candidate)
                if isinstance(tasks, list) and len(tasks) > 0:
                    return [self._normalize_task(t) for t in tasks]
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 3: Parse numbered list / markdown headings
        tasks = []
        lines = plan_text.strip().split("\n")
        current_task = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Match "1. Title", "- Title", "* Title", "## Title"
            if re.match(r"^(\d+[\.\)]\s+|[-*]\s+|#{1,3}\s+)", line):
                if current_task:
                    tasks.append(current_task)
                title = re.sub(r"^(\d+[\.\)]\s+|[-*]\s+|#{1,3}\s+)", "", line).strip()
                title = re.sub(r"\*\*(.+?)\*\*", r"\1", title)  # Remove bold markers
                if title and len(title) > 3:
                    current_task = {
                        "title": title[:200],
                        "description": title,
                        "acceptance_criteria": "Task completed successfully with working code",
                        "assigned_role": self._guess_role(title),
                        "risk_level": "medium",
                        "effort_estimate": "medium",
                        "dependencies": [],
                        "reviewer_role": "backend_dev",
                    }
                else:
                    current_task = None
            elif current_task and line:
                current_task["description"] += f" {line}"

        if current_task:
            tasks.append(current_task)

        if tasks:
            return [self._normalize_task(t) for t in tasks]

        # Strategy 4: Fallback — create smart tasks from the original request
        return self._create_fallback_tasks(original_request or plan_text[:500])

    def _normalize_task(self, t: dict) -> dict:
        """Ensure a task dict has all required fields."""
        role = t.get("assigned_role", "fullstack").lower().replace(" ", "_")
        valid_roles = {"project_manager", "ux_designer", "frontend_dev", "backend_dev", "fullstack", "research", "db_engineer"}
        if role not in valid_roles:
            role = self._guess_role(t.get("title", "") + " " + t.get("description", ""))

        return {
            "title": t.get("title", "Untitled Task")[:200],
            "description": t.get("description", t.get("title", ""))[:2000],
            "acceptance_criteria": t.get("acceptance_criteria", "Task completed with working code")[:1000],
            "assigned_role": role,
            "risk_level": t.get("risk_level", "medium").lower(),
            "effort_estimate": t.get("effort_estimate", "medium").lower(),
            "dependencies": t.get("dependencies", []),
            "reviewer_role": t.get("reviewer_role", "backend_dev"),
        }

    def _guess_role(self, text: str) -> str:
        """Guess the best agent role from task text."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["react", "component", "ui", "css", "frontend", "layout", "page", "button"]):
            return "frontend_dev"
        if any(w in text_lower for w in ["api", "endpoint", "route", "server", "fastapi", "backend", "auth"]):
            return "backend_dev"
        if any(w in text_lower for w in ["database", "schema", "sql", "migration", "table", "model"]):
            return "db_engineer"
        if any(w in text_lower for w in ["design", "ux", "wireframe", "color", "typography"]):
            return "ux_designer"
        if any(w in text_lower for w in ["research", "analyze", "evaluate", "compare"]):
            return "research"
        return "fullstack"

    def _create_fallback_tasks(self, request: str) -> list[dict]:
        """Create meaningful default tasks when PM output can't be parsed."""
        tasks = []
        req_lower = request.lower()

        # Always create a backend task if request mentions API/server/backend
        if any(w in req_lower for w in ["api", "backend", "server", "endpoint", "auth", "database"]):
            tasks.append({
                "title": "Implement backend API",
                "description": f"Build the backend API for: {request[:300]}",
                "acceptance_criteria": "Working API endpoints with proper error handling",
                "assigned_role": "backend_dev",
                "risk_level": "medium",
                "effort_estimate": "medium",
                "dependencies": [],
                "reviewer_role": "fullstack",
            })

        # Always create a frontend task if request mentions UI/frontend
        if any(w in req_lower for w in ["ui", "frontend", "react", "page", "component", "app", "interface", "dashboard"]):
            tasks.append({
                "title": "Implement frontend UI",
                "description": f"Build the frontend interface for: {request[:300]}",
                "acceptance_criteria": "Working React components with proper state management",
                "assigned_role": "frontend_dev",
                "risk_level": "medium",
                "effort_estimate": "medium",
                "dependencies": [],
                "reviewer_role": "ux_designer",
            })

        # Database task if relevant
        if any(w in req_lower for w in ["database", "db", "schema", "table", "sql", "data model"]):
            tasks.append({
                "title": "Design database schema",
                "description": f"Create database models for: {request[:300]}",
                "acceptance_criteria": "SQLAlchemy models with proper relationships and migrations",
                "assigned_role": "db_engineer",
                "risk_level": "medium",
                "effort_estimate": "small",
                "dependencies": [],
                "reviewer_role": "backend_dev",
            })

        # If nothing specific matched, create a fullstack task
        if not tasks:
            tasks.append({
                "title": "Implement full-stack solution",
                "description": f"Build complete implementation for: {request[:500]}",
                "acceptance_criteria": "Working implementation with both frontend and backend code",
                "assigned_role": "fullstack",
                "risk_level": "medium",
                "effort_estimate": "large",
                "dependencies": [],
                "reviewer_role": "backend_dev",
            })

        return tasks

    def _get_ext_for_role(self, role: str) -> str:
        """Get the default file extension for an agent role."""
        return {
            "frontend_dev": ".tsx",
            "backend_dev": ".py",
            "fullstack": ".py",
            "db_engineer": ".py",
            "ux_designer": ".md",
            "research": ".md",
            "project_manager": ".md",
        }.get(role, ".txt")

    # ------------------------------------------------------------------
    # DB task creation
    # ------------------------------------------------------------------

    def _create_db_tasks(self, db: Session, tasks: list[dict], project_name: str) -> list:
        from backend.models.task import Task
        from backend.models.agent import Agent, AgentRole

        db_tasks = []
        for t in tasks:
            role_str = t.get("assigned_role", "fullstack").lower()
            try:
                role_enum = AgentRole(role_str)
            except ValueError:
                role_enum = AgentRole.FULLSTACK

            agent = db.query(Agent).filter(Agent.role == role_enum).first()

            risk_str = t.get("risk_level", "medium").lower()
            try:
                risk_enum = RiskLevel(risk_str)
            except ValueError:
                risk_enum = RiskLevel.MEDIUM

            task = Task(
                title=t.get("title", "Untitled"),
                description=t.get("description", ""),
                acceptance_criteria=t.get("acceptance_criteria", ""),
                status=TaskStatus.BACKLOG,
                owner_agent_id=agent.id if agent else None,
                risk_level=risk_enum,
                effort_estimate=t.get("effort_estimate", "medium"),
                project_name=project_name,
            )
            db.add(task)
            db_tasks.append(task)

        db.commit()
        for task in db_tasks:
            db.refresh(task)
        return db_tasks

    # ------------------------------------------------------------------
    # Progress logging
    # ------------------------------------------------------------------

    def _log_progress(self, workflow_id: str, stage: str, message: str):
        if workflow_id in self._active_workflows:
            entry = {
                "stage": stage,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._active_workflows[workflow_id]["progress"].append(entry)
            logger.info(f"[Workflow {workflow_id}] [{stage}] {message}")

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        return self._active_workflows.get(workflow_id)

    def list_workflows(self) -> list[dict]:
        return [
            {"id": k, "status": v["status"], "task_count": v.get("task_count", 0)}
            for k, v in self._active_workflows.items()
        ]


orchestrator = Orchestrator()
