import sqlite3
from typing import Dict, Any
from .providers import get_ai_provider


class TaskPlanner:
    """Transforms natural language user goals into structured, prioritized subtask plans."""

    def __init__(self):
        self.provider = get_ai_provider()

    def plan(
        self,
        goal: str,
        intent_data: Dict[str, Any],
        memory_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.provider.generate_plan(goal, intent_data, memory_context)
