import logging
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ShortTermMemory:
    def __init__(self):
        self._store: dict[str, dict] = {}

    def create_context(self, context_id: str, data: Optional[dict] = None):
        self._store[context_id] = data or {
            "messages": [],
            "decisions": [],
            "artifacts": [],
            "metadata": {},
        }

    def add_message(self, context_id: str, role: str, content: str):
        if context_id not in self._store:
            self.create_context(context_id)
        self._store[context_id]["messages"].append({
            "role": role,
            "content": content,
        })

    def add_decision(self, context_id: str, decision: dict):
        if context_id not in self._store:
            self.create_context(context_id)
        self._store[context_id]["decisions"].append(decision)

    def add_artifact(self, context_id: str, artifact: dict):
        if context_id not in self._store:
            self.create_context(context_id)
        self._store[context_id]["artifacts"].append(artifact)

    def get_context(self, context_id: str) -> Optional[dict]:
        return self._store.get(context_id)

    def get_messages(self, context_id: str, limit: int = 20) -> list[dict]:
        ctx = self._store.get(context_id, {})
        return ctx.get("messages", [])[-limit:]

    def clear_context(self, context_id: str):
        self._store.pop(context_id, None)

    def list_contexts(self) -> list[str]:
        return list(self._store.keys())


short_term_memory = ShortTermMemory()
