import sqlite3
import datetime
from typing import Dict, Any
from .base import BaseTool, ToolResult


class NotificationTool(BaseTool):
    name = "notification_tool"
    description = "Simulate and dispatch in-app notifications and urgent alerts to the user."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Alert title."
            },
            "message": {
                "type": "string",
                "description": "Notification content body."
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "normal", "high", "critical"],
                "description": "Urgency level of the notification."
            }
        },
        "required": ["title", "message"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        title = kwargs.get("title", "")
        message = kwargs.get("message", "")
        urgency = kwargs.get("urgency", "normal")
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        notification_payload = {
            "title": title,
            "message": message,
            "urgency": urgency,
            "timestamp": timestamp,
            "status": "DELIVERED_SIMULATED",
            "channel": "TaskPilot In-App Push"
        }

        return ToolResult(
            success=True,
            data=notification_payload,
            message=f"Notification dispatched successfully: [{urgency.upper()}] '{title}'"
        )
