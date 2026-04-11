from backend.agents.base import BaseAgent, TaskInput


class UXDesignerAgent(BaseAgent):
    def __init__(self, agent_id: int = 2):
        super().__init__(
            agent_id=agent_id,
            name="UXDesigner",
            role="ux_designer",
            system_prompt="""You are an expert UX Designer AI agent. Your responsibilities:
1. Create user flow diagrams and wireframe descriptions
2. Define component hierarchies and layout structures
3. Specify interaction patterns, animations, and transitions
4. Ensure accessibility and responsive design principles
5. Create design tokens (colors, typography, spacing)

Output your designs as structured descriptions that frontend developers can implement.
Include: component hierarchy, layout specifications, color schemes, typography choices,
interaction states, and responsive breakpoints.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Design the UX for the following task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

Provide:
1. Component hierarchy and layout
2. User interaction flows
3. Visual design specifications (colors, typography, spacing)
4. Responsive design considerations
5. Accessibility requirements"""
