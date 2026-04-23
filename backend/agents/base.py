import json
import re
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


# ---------------------------------------------------------------------------
# File-extraction helpers
# ---------------------------------------------------------------------------

# Pattern: ```lang\n# file: path/to/file.ext  OR  // file: path/to/file.ext
_CODE_BLOCK_RE = re.compile(
    r"```(\w*)\s*\n"
    r"(?:#|//|<!--|/\*)\s*(?:file|filename|FILE|FILENAME)\s*:\s*(.+?)\s*(?:-->|\*/)?\s*\n"
    r"(.*?)"
    r"\n```",
    re.DOTALL,
)

# Pattern: --- FILE: path/to/file.ext ---
_FILE_MARKER_RE = re.compile(
    r"---\s*FILE:\s*(.+?)\s*---\s*\n"
    r"```\w*\s*\n(.*?)\n```",
    re.DOTALL,
)

# Simpler fallback: ```lang  filename.ext\n...```
_SIMPLE_BLOCK_RE = re.compile(
    r"```(\w+)\s+([\w./\-]+\.\w+)\s*\n(.*?)\n```",
    re.DOTALL,
)

LANG_EXT = {
    "python": ".py", "py": ".py",
    "javascript": ".js", "js": ".js",
    "typescript": ".ts", "ts": ".ts",
    "tsx": ".tsx", "jsx": ".jsx",
    "css": ".css", "html": ".html",
    "json": ".json", "yaml": ".yaml", "yml": ".yml",
    "sql": ".sql", "sh": ".sh", "bash": ".sh",
    "dockerfile": "Dockerfile", "docker": "Dockerfile",
    "toml": ".toml", "ini": ".ini", "cfg": ".cfg",
    "md": ".md", "markdown": ".md",
}


def extract_files_from_output(text: str) -> list[tuple[str, str, str]]:
    """Extract (filename, content, file_type) tuples from LLM output.

    Tries multiple patterns to find embedded code files.
    Returns an empty list if no files are found.
    """
    files: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    # Strategy 1: --- FILE: path --- markers
    for m in _FILE_MARKER_RE.finditer(text):
        fname, content = m.group(1).strip(), m.group(2).strip()
        if fname not in seen:
            seen.add(fname)
            files.append((fname, content, _guess_type(fname)))

    # Strategy 2: ```lang\n# file: path
    for m in _CODE_BLOCK_RE.finditer(text):
        fname, content = m.group(2).strip(), m.group(3).strip()
        if fname not in seen:
            seen.add(fname)
            files.append((fname, content, _guess_type(fname)))

    # Strategy 3: ```lang filename.ext
    for m in _SIMPLE_BLOCK_RE.finditer(text):
        lang, fname, content = m.group(1), m.group(2).strip(), m.group(3).strip()
        if fname not in seen:
            seen.add(fname)
            files.append((fname, content, _guess_type(fname)))

    # Strategy 4: If nothing matched but there are code blocks, create
    # numbered files from the fenced blocks
    if not files:
        blocks = re.findall(r"```(\w*)\n(.*?)\n```", text, re.DOTALL)
        for idx, (lang, content) in enumerate(blocks, 1):
            content = content.strip()
            if len(content) < 10:
                continue
            ext = LANG_EXT.get(lang.lower(), ".txt")
            fname = f"output_{idx}{ext}"
            files.append((fname, content, _guess_type(fname)))

    return files


def _guess_type(fname: str) -> str:
    ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
    if ext in ("py", "js", "ts", "tsx", "jsx", "java", "go", "rs", "cpp", "c", "rb"):
        return "code"
    if ext in ("css", "scss", "less"):
        return "style"
    if ext in ("html", "md", "txt", "rst"):
        return "document"
    if ext in ("json", "yaml", "yml", "toml", "ini", "cfg", "env"):
        return "config"
    if ext in ("sql",):
        return "sql"
    return "code"


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
            primary_model="codellama-7b-instruct",
            max_tokens=4096,
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
        """Parse LLM response, extracting individual files as attachments."""
        content = response.content

        # Extract structured files from the response
        extracted_files = extract_files_from_output(content)
        attachments = [
            Attachment(filename=fname, content=fcontent, file_type=ftype)
            for fname, fcontent, ftype in extracted_files
        ]

        return AgentOutput(
            reasoning_summary=f"Agent {self.name} processed task: {task_input.title}",
            solution_artifact=content,
            attachments=attachments,
            validation_checklist=[
                {"item": "Output generated", "passed": True},
                {"item": "Response non-empty", "passed": len(content) > 0},
                {"item": "Files extracted", "passed": len(attachments) > 0},
                {"item": f"File count: {len(attachments)}", "passed": True},
            ],
            metadata={
                "model": response.model,
                "tokens": response.tokens_used,
                "latency_ms": response.latency_ms,
                "files_extracted": len(attachments),
                "file_names": [a.filename for a in attachments],
            },
        )

    def _build_review_prompt(self, task_input: TaskInput, agent_output: AgentOutput) -> str:
        return f"""Review the following task output:

## Task
Title: {task_input.title}
Description: {task_input.description}
Acceptance Criteria: {task_input.acceptance_criteria}

## Output to Review
{agent_output.solution_artifact[:3000]}

## Files Produced
{chr(10).join(f'- {a.filename}' for a in agent_output.attachments) or 'No individual files extracted'}

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
