from typing import Dict, List, Optional, Any
import sqlite3
from .base import BaseTool, ToolResult
from .task_tool import TaskTool
from .reminder_tool import ReminderTool
from .schedule_tool import ScheduleTool
from .planning_tool import PlanningTool
from .search_tool import SearchKnowledgeTool
from .notification_tool import NotificationTool
from .simulated_tools import (
    GmailTool,
    SlackTool,
    GoogleCalendarTool,
    NotionTool,
    OutlookTool,
    TodoistTool
)


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        tools = [
            TaskTool(),
            ReminderTool(),
            ScheduleTool(),
            PlanningTool(),
            SearchKnowledgeTool(),
            NotificationTool(),
            # Extensible simulated tools
            GmailTool(),
            SlackTool(),
            GoogleCalendarTool(),
            NotionTool(),
            OutlookTool(),
            TodoistTool()
        ]
        for t in tools:
            self._tools[t.name] = t

    def register(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_all(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        return [t.to_spec() for t in self._tools.values()]

    def execute(self, tool_name: str, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered in ToolRegistry.",
                message=f"Tool '{tool_name}' not found."
            )
        return tool.execute(user_id=user_id, conn=conn, **kwargs)


# Global registry instance
default_registry = ToolRegistry()
