import re
import sqlite3
from typing import Dict, Any, Optional
from .providers import get_ai_provider
from .memory import AgentMemory


class IntentAnalyzer:
    """Understands user intent, extracts entities, and leverages stored preferences."""

    def __init__(self):
        self.provider = get_ai_provider()

    def analyze(self, user_id: int, conn: sqlite3.Connection, message: str) -> Dict[str, Any]:
        memory_ctx = AgentMemory.get_user_context(conn, user_id)

        # First check if user is updating preferences
        learned = AgentMemory.extract_and_store_preferences(conn, user_id, message)
        if learned:
            return {
                "intent": "MEMORY_UPDATE",
                "goal": message,
                "confidence": 1.0,
                "learned_memory": learned,
                "memory_context": memory_ctx,
                "entities": {"key": learned["key"], "value": learned["value"]}
            }

        # Analyze using configured AI provider
        analysis = self.provider.analyze_intent(message, memory_ctx)
        analysis["memory_context"] = memory_ctx

        # Refine task actions with regex entity extraction if applicable
        msg_lower = message.lower()

        # Priority extraction
        prio = "MEDIUM"
        if "urgent" in msg_lower:
            prio = "URGENT"
        elif "high priority" in msg_lower or "high" in msg_lower:
            prio = "HIGH"
        elif "low priority" in msg_lower or "low" in msg_lower:
            prio = "LOW"

        # Task ID extraction
        task_id = None
        id_match = re.search(r"#?(\d+)", message)
        if id_match:
            try:
                task_id = int(id_match.group(1))
            except ValueError:
                pass

        # Due date extraction
        due_date = None
        if "tomorrow" in msg_lower:
            due_date = "Tomorrow"
            time_match = re.search(r"(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", msg_lower)
            if time_match:
                due_date = f"Tomorrow at {time_match.group(1).upper()}"
        elif "friday" in msg_lower:
            due_date = "Friday at 5:00 PM"
        elif "next week" in msg_lower:
            due_date = "Next Week"

        if "entities" not in analysis:
            analysis["entities"] = {}

        analysis["entities"]["priority"] = prio
        if task_id is not None:
            analysis["entities"]["task_id"] = task_id
        if due_date is not None:
            analysis["entities"]["due_date"] = due_date

        return analysis
