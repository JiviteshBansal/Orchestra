from backend.agents.base import BaseAgent, TaskInput


class BackendDevAgent(BaseAgent):
    def __init__(self, agent_id: int = 4):
        super().__init__(
            agent_id=agent_id,
            name="BackendDev",
            role="backend_dev",
            system_prompt="""You are an expert Backend Developer AI agent specializing in Python and FastAPI.
Your responsibilities:
1. Design and implement RESTful API endpoints
2. Implement business logic and data processing
3. Create database queries and data access layers
4. Implement authentication, validation, and error handling
5. Write comprehensive unit and integration tests

Output your code as complete, production-ready Python files. Include:
- API route handlers
- Service/business logic modules
- Data access functions
- Pydantic schemas
- Test files

Follow Python best practices: type hints, async/await, proper error handling, logging.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        deps = ""
        if task_input.dependencies:
            deps = "\n\nDependency Outputs:\n" + "\n".join(
                str(d) for d in task_input.dependencies
            )

        return f"""Implement the following backend task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}
{deps}

Provide complete Python/FastAPI code files. Include API routes, business logic, tests."""
