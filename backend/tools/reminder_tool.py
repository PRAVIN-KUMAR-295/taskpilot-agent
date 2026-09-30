import sqlite3
from typing import Dict, Any
from .base import BaseTool, ToolResult
try:
    from database.repositories import ReminderRepository
except ImportError:
    from backend.database.repositories import ReminderRepository




class ReminderTool(BaseTool):
    name = "reminder_tool"
    description = "Create, cancel, or list intelligent reminders for tasks, assignments, and deadlines."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "cancel", "list"],
                "description": "Reminder operation."
            },
            "reminder_id": {
                "type": "integer",
                "description": "Required for cancel operation."
            },
            "task_id": {
                "type": "integer",
                "description": "Optional associated task ID."
            },
            "title": {
                "type": "string",
                "description": "Reminder text or topic."
            },
            "reminder_time": {
                "type": "string",
                "description": "Date/time string for reminder trigger (e.g. 'tomorrow at 6 PM', '2026-10-01 18:00')."
            },
            "channel": {
                "type": "string",
                "enum": ["in_app", "notification_tool", "email_simulated"],
                "description": "Notification delivery channel."
            }
        },
        "required": ["action"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        action = kwargs.get("action", "").lower()

        try:
            if action == "create":
                title = kwargs.get("title")
                reminder_time = kwargs.get("reminder_time")
                if not title or not reminder_time:
                    return ToolResult(success=False, error="Both 'title' and 'reminder_time' are required to create a reminder.")

                task_id = kwargs.get("task_id")
                channel = kwargs.get("channel", "in_app")

                reminder = ReminderRepository.create(
                    conn=conn,
                    user_id=user_id,
                    title=title,
                    reminder_time=reminder_time,
                    task_id=int(task_id) if task_id else None,
                    channel=channel
                )
                return ToolResult(
                    success=True,
                    data=reminder,
                    message=f"Reminder #{reminder['id']} set for '{reminder['title']}' at {reminder['reminder_time']}."
                )

            elif action == "cancel":
                reminder_id = kwargs.get("reminder_id")
                if not reminder_id:
                    return ToolResult(success=False, error="reminder_id is required to cancel a reminder.")
                cancelled = ReminderRepository.cancel(conn, int(reminder_id), user_id)
                if not cancelled:
                    return ToolResult(success=False, error=f"Reminder #{reminder_id} not found.")
                return ToolResult(
                    success=True,
                    data={"reminder_id": reminder_id, "status": "CANCELLED"},
                    message=f"Cancelled reminder #{reminder_id}."
                )

            elif action == "list":
                status = kwargs.get("status")
                reminders = ReminderRepository.list_by_user(conn, user_id, status=status)
                return ToolResult(
                    success=True,
                    data=reminders,
                    message=f"Retrieved {len(reminders)} reminders."
                )

            else:
                return ToolResult(success=False, error=f"Unknown reminder action: '{action}'.")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"ReminderTool failed: {str(e)}")
