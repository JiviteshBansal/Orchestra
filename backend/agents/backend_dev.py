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

CRITICAL OUTPUT FORMAT:
You MUST output complete, working Python files. Each file MUST be wrapped in a code fence with a FILE marker:

--- FILE: routes/users.py ---
```python
# file: routes/users.py
from fastapi import APIRouter, Depends
...
```

--- FILE: models/user.py ---
```python
# file: models/user.py
from sqlalchemy import Column, Integer, String
...
```

--- FILE: tests/test_users.py ---
```python
# file: tests/test_users.py
import pytest
...
```

Follow Python best practices: type hints, async/await, proper error handling, logging.
Always produce at least: one route file, one model/schema file, and one test file.""",
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

## Output Requirements
Provide COMPLETE Python/FastAPI code files ready for production.
Each file must be wrapped in its own code fence with a --- FILE: path/name.py --- marker above it.
Include at minimum: API routes, models/schemas, and test files."""
