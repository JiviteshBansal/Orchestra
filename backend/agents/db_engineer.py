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

Output complete database artifacts:
- Schema definitions (SQLAlchemy models)
- Migration scripts
- Index definitions
- Query examples
- Data validation rules""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Design the database solution for:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

Provide SQLAlchemy models, migration scripts, and optimized queries."""
