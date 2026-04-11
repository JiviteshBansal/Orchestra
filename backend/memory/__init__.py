from backend.memory.short_term import ShortTermMemory, short_term_memory
from backend.memory.long_term import LongTermMemory, long_term_memory


class MemoryManager:
    def __init__(self):
        self.short_term = short_term_memory
        self.long_term = long_term_memory

    def store_task_context(self, task_id: int, content: str, metadata: dict = None):
        ctx_id = f"task_{task_id}"
        self.short_term.add_message(ctx_id, "system", content)
        self.long_term.add(content, metadata={
            "task_id": task_id,
            **(metadata or {}),
        })

    def retrieve_relevant(self, query: str, top_k: int = 5) -> list[dict]:
        return self.long_term.search(query, top_k=top_k)

    def get_task_context(self, task_id: int) -> dict:
        return self.short_term.get_context(f"task_{task_id}") or {}


memory_manager = MemoryManager()

__all__ = [
    "ShortTermMemory", "short_term_memory",
    "LongTermMemory", "long_term_memory",
    "MemoryManager", "memory_manager",
]
