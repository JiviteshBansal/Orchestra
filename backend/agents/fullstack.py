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

CRITICAL OUTPUT FORMAT:
You MUST output complete, working code files. Each file MUST be wrapped in a code fence with a FILE marker:

--- FILE: backend/routes/users.py ---
```python
# file: backend/routes/users.py
from fastapi import APIRouter
...
```

--- FILE: frontend/src/components/UserList.tsx ---
```tsx
// file: frontend/src/components/UserList.tsx
import React from 'react';
...
```

Always produce at least one backend file and one frontend file.
Make sure API contracts match between the two layers.
Include proper error handling, type hints, and comments.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Implement the following full-stack task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

## Output Requirements
Provide COMPLETE implementation files for both frontend (React/TypeScript) and backend (Python/FastAPI).
Each file must be wrapped in its own code fence with a --- FILE: path/name.ext --- marker above it.
Ensure the API contracts are consistent between layers.
Include at minimum: one .py API file, one .tsx component file, and any needed type/schema files."""
