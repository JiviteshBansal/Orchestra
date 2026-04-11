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

Output your task breakdown as a structured JSON array with this format:
[{
    "title": "Task title",
    "description": "Detailed description",
    "acceptance_criteria": "Clear criteria for completion",
    "assigned_role": "agent_role (e.g., frontend_dev, backend_dev)",
    "risk_level": "low|medium|high|critical",
    "effort_estimate": "small|medium|large|xlarge",
    "dependencies": [],
    "reviewer_role": "role of the reviewing agent"
}]

Be thorough, specific, and practical. Each task should be independently executable.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        context_str = ""
        if task_input.context:
            context_str = f"\n\nAdditional Context:\n{task_input.context}"

        return f"""Break down the following project request into concrete, actionable tasks:

## Project Request
{task_input.description}

## Requirements
{task_input.acceptance_criteria}
{context_str}

Create a detailed task breakdown with assignments, dependencies, and effort estimates.
Each task should be small enough for a single agent to complete in one execution cycle.
Output as a JSON array of task objects."""
