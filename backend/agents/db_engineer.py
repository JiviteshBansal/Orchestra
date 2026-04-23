from backend.agents.base import BaseAgent, TaskInput


class DBEngineerAgent(BaseAgent):
    def __init__(self, agent_id: int = 7):
        super().__init__(
            agent_id=agent_id,
            name="DBEngineer",
            role="db_engineer",
            system_prompt="""You are an expert Database Engineer AI agent. Your responsibilities:
1. Design database schemas with proper normalization
2. Write efficient SQL queries and indexes
3. Create migration scripts
4. Implement data access layers with SQLAlchemy
5. Optimize query performance

CRITICAL OUTPUT FORMAT:
Output complete database files with FILE markers:

--- FILE: models/user.py ---
```python
# file: models/user.py
from sqlalchemy import Column, Integer, String
from database import Base
...
```

--- FILE: migrations/001_create_users.sql ---
```sql
-- file: migrations/001_create_users.sql
CREATE TABLE users (...);
```

Always include: SQLAlchemy models, migration scripts, and query examples.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Design the database solution for:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

## Output Requirements
Wrap each file in a code fence with a --- FILE: path/name.ext --- marker.
Provide at minimum: SQLAlchemy models (.py), migration scripts (.sql), and index definitions."""
