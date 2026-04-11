import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

from backend.llm.gateway import llm_gateway, ModelProfile, LLMResponse

logger = logging.getLogger(__name__)


@dataclass
class TaskInput:
    task_id: int
    title: str
    description: str
    acceptance_criteria: str = ""
    dependencies: list[dict] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    project_name: str = "default"


@dataclass
class Attachment:
    filename: str
    content: str
    file_type: str = "code"


@dataclass
class AgentOutput:
    reasoning_summary: str = ""
    solution_artifact: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    validation_checklist: list[dict] = field(default_factory=list)
    status: str = "completed"
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "reasoning_summary": self.reasoning_summary,
            "solution_artifact": self.solution_artifact,
            "attachments": [
                {"filename": a.filename, "content": a.content, "file_type": a.file_type}
                for a in self.attachments
            ],
            "validation_checklist": self.validation_checklist,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class ReviewFeedback:
    approved: bool
    comments: str = ""
    suggestions: list[str] = field(default_factory=list)
    severity: str = "info"

    def to_dict(self) -> dict:
        return {
            "approved": self.approved,
            "comments": self.comments,
            "suggestions": self.suggestions,
            "severity": self.severity,
        }


class BaseAgent(ABC):
    def __init__(
        self,
        agent_id: int,
        name: str,
        role: str,
        system_prompt: str = "",
        model_profile: Optional[ModelProfile] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.model_profile = model_profile or ModelProfile(
            primary_model="codellama-7b-instruct"
        )
        self.logger = logging.getLogger(f"agent.{name}")

    async def execute(self, task_input: TaskInput) -> AgentOutput:
        self.logger.info(f"[{self.name}] Starting task: {task_input.title}")
        try:
            prompt = self._build_prompt(task_input)
            response = await llm_gateway.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                model_profile=self.model_profile,
            )
            if not response.success:
                return AgentOutput(
                    status="failed",
                    error=f"LLM call failed: {response.error}",
                )
            output = self._parse_response(response, task_input)
            self.logger.info(f"[{self.name}] Task completed: {task_input.title}")
            return output
        except Exception as e:
            self.logger.error(f"[{self.name}] Error: {e}")
            return AgentOutput(status="failed", error=str(e))

    async def review(self, task_input: TaskInput, agent_output: AgentOutput) -> ReviewFeedback:
        self.logger.info(f"[{self.name}] Reviewing task: {task_input.title}")
        review_prompt = self._build_review_prompt(task_input, agent_output)
        response = await llm_gateway.generate(
            prompt=review_prompt,
            system_prompt=f"You are {self.name}, a {self.role} reviewer. Provide constructive review feedback.",
            model_profile=self.model_profile,
        )
        if not response.success:
            return ReviewFeedback(approved=False, comments=f"Review failed: {response.error}")
        return self._parse_review(response)

    @abstractmethod
    def _build_prompt(self, task_input: TaskInput) -> str:
        pass

    def _parse_response(self, response: LLMResponse, task_input: TaskInput) -> AgentOutput:
        return AgentOutput(
            reasoning_summary=f"Agent {self.name} processed task: {task_input.title}",
            solution_artifact=response.content,
            validation_checklist=[
                {"item": "Output generated", "passed": True},
                {"item": "Response non-empty", "passed": len(response.content) > 0},
            ],
            metadata={
                "model": response.model,
                "tokens": response.tokens_used,
                "latency_ms": response.latency_ms,
            },
        )

    def _build_review_prompt(self, task_input: TaskInput, agent_output: AgentOutput) -> str:
        return f"""Review the following task output:

## Task
Title: {task_input.title}
Description: {task_input.description}
Acceptance Criteria: {task_input.acceptance_criteria}

## Output to Review
{agent_output.solution_artifact}

## Instructions
1. Check if the output meets the acceptance criteria
2. Identify any issues, bugs, or improvements
3. Provide your verdict: APPROVE or REVISE

Respond in this format:
VERDICT: [APPROVE/REVISE]
COMMENTS: [Your detailed feedback]
SUGGESTIONS:
- [Suggestion 1]
- [Suggestion 2]
"""

    def _parse_review(self, response: LLMResponse) -> ReviewFeedback:
        content = response.content.upper()
        approved = "APPROVE" in content and "REVISE" not in content
        return ReviewFeedback(
            approved=approved,
            comments=response.content,
            suggestions=[],
        )
