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

CRITICAL OUTPUT FORMAT:
You MUST output complete, working code files. Each file MUST be wrapped in a code fence with a FILE marker:

--- FILE: src/components/UserList.tsx ---
```tsx
// file: src/components/UserList.tsx
import React, { useState, useEffect } from 'react';
...
```

--- FILE: src/styles/UserList.css ---
```css
/* file: src/styles/UserList.css */
.user-list { ... }
```

--- FILE: src/types/user.ts ---
```typescript
// file: src/types/user.ts
export interface User { ... }
```

Always follow React best practices: functional components, hooks, proper error boundaries.
Always produce at least: one .tsx component, one .css style file, and one types/interface file.""",
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

## Output Requirements
Provide COMPLETE React + TypeScript code files ready for implementation.
Each file must be wrapped in its own code fence with a --- FILE: path/name.ext --- marker above it.
Include at minimum: component code (.tsx), styles (.css), and type definitions (.ts)."""
