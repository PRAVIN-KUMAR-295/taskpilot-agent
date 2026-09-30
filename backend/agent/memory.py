import re
import sqlite3
try:
    from database.repositories import MemoryRepository
except ImportError:
    from backend.database.repositories import MemoryRepository



class AgentMemory:
    """Manages user-level memory preferences, habits, and constraints."""

    @staticmethod
    def get_user_context(conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
        """Loads all stored preferences for a user into a clean dictionary."""
        memories = MemoryRepository.get_all(conn, user_id)
        context = {}
        for m in memories:
            context[m["key"]] = m["value"]
        return context

    @staticmethod
    def extract_and_store_preferences(conn: sqlite3.Connection, user_id: int, message: str) -> Optional[Dict[str, Any]]:
        """
        Detects if user expresses a preference or working habit, and persists it.
        Example: 'I prefer studying in the evening' or 'My working hours are 9 AM - 5 PM'.
        """
        msg = message.strip()
        lower = msg.lower()

        # Study time preference
        if "study" in lower and ("evening" in lower or "night" in lower or "morning" in lower or "afternoon" in lower):
            val = "evening (07:00 PM - 09:00 PM)" if ("evening" in lower or "night" in lower) else "morning (08:00 AM - 11:00 AM)"
            return MemoryRepository.set(
                conn, user_id,
                key="preferred_evening_focus",
                value=val,
                category="habit",
                source="user_chat"
            )

        # Working hours preference
        match_hours = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", lower)
        if match_hours and ("work" in lower or "hour" in lower or "available" in lower):
            val = f"{match_hours.group(1).upper()} - {match_hours.group(2).upper()}"
            return MemoryRepository.set(
                conn, user_id,
                key="preferred_working_hours",
                value=val,
                category="work_hours",
                source="user_chat"
            )

        # Priority preference
        if "prefer" in lower and ("high priority" in lower or "urgent" in lower):
            return MemoryRepository.set(
                conn, user_id,
                key="preferred_task_priority",
                value="Prioritize HIGH and URGENT tasks first",
                category="preference",
                source="user_chat"
            )

        return None
