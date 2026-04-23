from backend.agents.base import BaseAgent, TaskInput, AgentOutput


class ProjectManagerAgent(BaseAgent):
    def __init__(self, agent_id: int = 1):
        super().__init__(
            agent_id=agent_id,
            name="ProjectManager",
            role="project_manager",
            system_prompt="""You are an expert Project Manager AI agent. Your responsibilities:
1. Break down user requests into well-defined tasks with clear acceptance criteria
2. Estimate effort and risk for each task
3. Define task dependencies and execution order
4. Assign tasks to the most appropriate agent based on their capabilities

Available agent roles you can assign:
- frontend_dev: React/TypeScript UI components, pages, styling
- backend_dev: Python/FastAPI endpoints, business logic, database
- fullstack: End-to-end features spanning front and back
- ux_designer: Wireframes, user flows, design specifications
- db_engineer: Database schema, migrations, queries
- research: Technical research, architecture analysis

CRITICAL: You MUST output your task breakdown as a JSON array wrapped in ```json fences.
Each task object must have these fields:
- title: short descriptive task title
- description: detailed description of what to implement
- acceptance_criteria: specific, testable criteria
- assigned_role: one of the roles listed above
- risk_level: low | medium | high | critical
- effort_estimate: small | medium | large | xlarge
- dependencies: array of task indices (0-based) this depends on
- reviewer_role: which role should review this task

Example output format:
```json
[
  {
    "title": "Create user authentication API",
    "description": "Implement JWT-based auth with login/signup endpoints...",
    "acceptance_criteria": "POST /auth/login returns JWT token; POST /auth/signup creates user",
    "assigned_role": "backend_dev",
    "risk_level": "medium",
    "effort_estimate": "medium",
    "dependencies": [],
    "reviewer_role": "fullstack"
  }
]
```

Be thorough and specific. Create 2-6 tasks. Each task should be independently executable.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        context_str = ""
        if task_input.context:
            context_str = f"\n\nAdditional Context:\n{task_input.context}"

        return f"""Break down the following project request into concrete, actionable tasks.

## Project Request
{task_input.description}

## Requirements
{task_input.acceptance_criteria}
{context_str}

Create a detailed task breakdown with assignments, dependencies, and effort estimates.
Each task should be small enough for a single agent to complete in one execution cycle.

IMPORTANT: Output ONLY a JSON array wrapped in ```json fences. No other text before or after.
"""
