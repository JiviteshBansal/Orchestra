from backend.agents.base import BaseAgent, TaskInput


class FrontendDevAgent(BaseAgent):
    def __init__(self, agent_id: int = 3):
        super().__init__(
            agent_id=agent_id,
            name="FrontendDev",
            role="frontend_dev",
            system_prompt="""You are an expert Frontend Developer AI agent specializing in React and TypeScript.
Your responsibilities:
1. Implement React components with TypeScript
2. Create responsive, accessible UIs
3. Implement state management and API integration
4. Write CSS/styled-components for pixel-perfect designs
5. Ensure cross-browser compatibility

Output your code as complete, ready-to-use files. Include:
- Component files (.tsx)
- Style files (.css or styled-components)
- Type definitions
- Unit test outlines

Always follow React best practices: functional components, hooks, proper error boundaries.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        deps = ""
        if task_input.dependencies:
            deps = "\n\nDependency Outputs:\n" + "\n".join(
                str(d) for d in task_input.dependencies
            )

        return f"""Implement the following frontend task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}
{deps}

Provide complete React + TypeScript code files ready for implementation.
Include component code, styles, types, and test cases."""
