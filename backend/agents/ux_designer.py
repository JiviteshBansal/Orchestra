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

CRITICAL OUTPUT FORMAT:
Output your design specs as structured files with FILE markers:

--- FILE: design/wireframes.md ---
```markdown
# file: design/wireframes.md
## Component Hierarchy
...
```

--- FILE: design/tokens.css ---
```css
/* file: design/tokens.css */
:root { --primary: #...; }
```

Include: component hierarchy, layout specs, color schemes, typography, interaction states.""",
        )

    def _build_prompt(self, task_input: TaskInput) -> str:
        return f"""Design the UX for the following task:

## Task: {task_input.title}
{task_input.description}

## Acceptance Criteria
{task_input.acceptance_criteria}

## Output Requirements
Wrap each deliverable in a code fence with a --- FILE: path/name.ext --- marker.
Provide:
1. Component hierarchy and layout (as .md)
2. Design tokens / CSS variables (as .css)
3. User interaction flows (as .md)
4. Responsive design specifications"""
