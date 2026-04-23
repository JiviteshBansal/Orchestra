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

CRITICAL OUTPUT FORMAT:
Output structured research as files with FILE markers:

--- FILE: research/analysis.md ---
```markdown
# file: research/analysis.md
## Problem Analysis
...
## Options Considered
...
## Recommendation
...
```

--- FILE: research/architecture.md ---
```markdown
# file: research/architecture.md
## System Architecture
...
```

Include: problem analysis, options with pros/cons, recommendation, implementation guidelines.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Research the following topic:

## Task: {task_input.title}
{task_input.description}

## Expected Output
{task_input.acceptance_criteria}

## Output Requirements
Wrap each deliverable in a code fence with a --- FILE: path/name.ext --- marker.
Provide a thorough, structured research report with analysis, options, and recommendations."""
