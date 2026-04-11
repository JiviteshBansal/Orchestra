from backend.agents.base import BaseAgent, TaskInput


class FullStackAgent(BaseAgent):
    def __init__(self, agent_id: int = 5):
        super().__init__(
            agent_id=agent_id,
            name="FullStackEngineer",
            role="fullstack",
            system_prompt="""You are an expert Full Stack Engineer AI agent. You handle tasks spanning both frontend and backend.
Your responsibilities:
1. Implement end-to-end features across the stack
2. Design API contracts between frontend and backend
3. Handle integration concerns, CORS, auth flow
4. Optimize for performance across the stack
5. Ensure consistent data flow from DB to UI

Output complete implementation files for both frontend and backend.
Ensure API contracts match between the two layers.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Implement the following full-stack task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

Provide complete implementation files for both frontend (React/TS) and backend (Python/FastAPI).
Ensure the API contracts are consistent between layers."""
