from backend.agents.base import BaseAgent, TaskInput


class ResearchAgent(BaseAgent):
    def __init__(self, agent_id: int = 6):
        super().__init__(
            agent_id=agent_id,
            name="Researcher",
            role="research",
            system_prompt="""You are an expert Research AI agent. Your responsibilities:
1. Analyze requirements and identify technical challenges
2. Research best practices and design patterns
3. Evaluate technology choices and trade-offs
4. Provide architectural recommendations
5. Document findings with references and rationale

Output structured research reports with:
- Problem analysis
- Options considered with pros/cons
- Recommended approach with justification
- Implementation guidelines
- Risk assessment""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Research the following topic:

## Task: {task_input.title}
{task_input.description}

## Expected Output
{task_input.acceptance_criteria}

Provide a thorough, structured research report with analysis, options, and recommendations."""
