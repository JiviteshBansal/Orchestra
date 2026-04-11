import json
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path

from backend.config import settings
from backend.memory import memory_manager

logger = logging.getLogger(__name__)


class PlaybookEntry:
    def __init__(self, title: str, context: str, actions: list[str], outcome: str):
        self.title = title
        self.context = context
        self.actions = actions
        self.outcome = outcome
        self.created_at = datetime.utcnow().isoformat()
        self.version = 1

    def to_dict(self):
        return {
            "title": self.title,
            "context": self.context,
            "actions": self.actions,
            "outcome": self.outcome,
            "created_at": self.created_at,
            "version": self.version,
        }


class DecisionRecord:
    def __init__(self, decision: str, rationale: str, alternatives: list[str], outcome: str = ""):
        self.decision = decision
        self.rationale = rationale
        self.alternatives = alternatives
        self.outcome = outcome
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "decision": self.decision,
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "outcome": self.outcome,
            "created_at": self.created_at,
        }


class ACEEngine:
    def __init__(self):
        self.playbooks: list[PlaybookEntry] = []
        self.decisions: list[DecisionRecord] = []
        self._versions: list[dict] = []
        self._store_path = Path(settings.VECTOR_STORE_PATH) / "ace"
        self._store_path.mkdir(parents=True, exist_ok=True)
        self._load()

    def learn_from_task(self, task_data: dict, output_data: dict, review_data: dict):
        if not review_data.get("approved", False):
            logger.info("Skipping learning from non-approved task")
            return

        playbook = PlaybookEntry(
            title=f"Playbook: {task_data.get('title', 'Unknown')}",
            context=task_data.get("description", ""),
            actions=[
                f"Assigned to: {task_data.get('assigned_role', 'unknown')}",
                f"Output summary: {str(output_data.get('reasoning_summary', ''))[:200]}",
            ],
            outcome=review_data.get("comments", "Approved"),
        )
        self.playbooks.append(playbook)

        decision = DecisionRecord(
            decision=f"Task '{task_data.get('title', '')}' implementation approach",
            rationale=output_data.get("reasoning_summary", ""),
            alternatives=[],
            outcome="Approved" if review_data.get("approved") else "Revised",
        )
        self.decisions.append(decision)

        memory_manager.long_term.add(
            json.dumps(playbook.to_dict()),
            metadata={"type": "playbook", "task": task_data.get("title", "")},
        )

        self._save()
        logger.info(f"ACE learned from task: {task_data.get('title', '')}")

    def get_context_pack(self, query: str, top_k: int = 5) -> dict:
        relevant = memory_manager.retrieve_relevant(query, top_k=top_k)
        return {
            "playbooks": [p.to_dict() for p in self.playbooks[-top_k:]],
            "decisions": [d.to_dict() for d in self.decisions[-top_k:]],
            "relevant_memories": relevant,
        }

    def get_prompt_improvement(self, agent_role: str) -> str:
        role_playbooks = [
            p for p in self.playbooks
            if agent_role in p.context.lower() or agent_role in str(p.actions).lower()
        ]
        if not role_playbooks:
            return ""
        tips = []
        for pb in role_playbooks[-3:]:
            tips.append(f"- Previous success: {pb.title} -> {pb.outcome}")
        return "\n\nLearned patterns:\n" + "\n".join(tips)

    def rollback(self, version: int) -> bool:
        if version < 0 or version >= len(self._versions):
            return False
        snapshot = self._versions[version]
        self.playbooks = [PlaybookEntry(**p) for p in snapshot.get("playbooks", [])]
        self.decisions = [DecisionRecord(**d) for d in snapshot.get("decisions", [])]
        self._save()
        logger.info(f"ACE rolled back to version {version}")
        return True

    def _save(self):
        self._versions.append({
            "playbooks": [p.to_dict() for p in self.playbooks],
            "decisions": [d.to_dict() for d in self.decisions],
            "timestamp": datetime.utcnow().isoformat(),
        })
        data = {
            "playbooks": [p.to_dict() for p in self.playbooks],
            "decisions": [d.to_dict() for d in self.decisions],
            "version_count": len(self._versions),
        }
        with open(self._store_path / "ace_data.json", "w") as f:
            json.dump(data, f, indent=2)

    def _load(self):
        data_path = self._store_path / "ace_data.json"
        if data_path.exists():
            try:
                with open(data_path) as f:
                    data = json.load(f)
                self.playbooks = [PlaybookEntry(**p) for p in data.get("playbooks", [])]
                self.decisions = [DecisionRecord(**d) for d in data.get("decisions", [])]
                logger.info(f"ACE loaded: {len(self.playbooks)} playbooks, {len(self.decisions)} decisions")
            except Exception as e:
                logger.error(f"ACE load failed: {e}")

    def get_stats(self) -> dict:
        return {
            "playbook_count": len(self.playbooks),
            "decision_count": len(self.decisions),
            "version_count": len(self._versions),
        }


ace_engine = ACEEngine()
