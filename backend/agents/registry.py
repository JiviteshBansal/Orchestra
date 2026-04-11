import logging
from typing import Optional
from backend.agents.base import BaseAgent
from backend.agents.pm import ProjectManagerAgent
from backend.agents.ux_designer import UXDesignerAgent
from backend.agents.frontend_dev import FrontendDevAgent
from backend.agents.backend_dev import BackendDevAgent
from backend.agents.fullstack import FullStackAgent
from backend.agents.research import ResearchAgent
from backend.agents.db_engineer import DBEngineerAgent

logger = logging.getLogger(__name__)

ROLE_TO_CLASS = {
    "project_manager": ProjectManagerAgent,
    "ux_designer": UXDesignerAgent,
    "frontend_dev": FrontendDevAgent,
    "backend_dev": BackendDevAgent,
    "fullstack": FullStackAgent,
    "research": ResearchAgent,
    "db_engineer": DBEngineerAgent,
}

ROLE_REVIEWER_MAP = {
    "project_manager": "research",
    "ux_designer": "frontend_dev",
    "frontend_dev": "ux_designer",
    "backend_dev": "fullstack",
    "fullstack": "backend_dev",
    "research": "project_manager",
    "db_engineer": "backend_dev",
}


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._initialize_defaults()

    def _initialize_defaults(self):
        for role, cls in ROLE_TO_CLASS.items():
            agent = cls()
            self._agents[role] = agent
            logger.info(f"Registered agent: {agent.name} ({role})")

    def get_agent(self, role: str) -> Optional[BaseAgent]:
        return self._agents.get(role)

    def get_reviewer_for(self, role: str) -> Optional[BaseAgent]:
        reviewer_role = ROLE_REVIEWER_MAP.get(role)
        if reviewer_role:
            return self._agents.get(reviewer_role)
        return None

    def list_agents(self) -> list[dict]:
        return [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "role": agent.role,
            }
            for agent in self._agents.values()
        ]

    def get_all(self) -> dict[str, BaseAgent]:
        return dict(self._agents)


agent_registry = AgentRegistry()
