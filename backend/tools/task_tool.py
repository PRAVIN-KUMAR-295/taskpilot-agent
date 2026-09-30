import sqlite3
from typing import Dict, Any, Optional, Tuple, List
from .base import BaseTool, ToolResult
try:
    from database.repositories import TaskRepository
except ImportError:
    from backend.database.repositories import TaskRepository




class TaskTool(BaseTool):
    name = "task_tool"
    description = "Create, update, complete, delete, or list user tasks. Supports priority, deadlines, and categories."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update", "delete", "complete", "list"],
                "description": "The task operation to perform."
            },
            "task_id": {
                "type": "integer",
                "description": "Required for update, delete, or complete operations."
            },
            "title": {
                "type": "string",
                "description": "Title of the task."
            },
            "description": {
                "type": "string",
                "description": "Optional detailed description of the task."
            },
            "priority": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"],
                "description": "Priority level."
            },
            "status": {
                "type": "string",
                "enum": ["TODO", "IN_PROGRESS", "COMPLETED", "BLOCKED"],
                "description": "Task status."
            },
            "due_date": {
                "type": "string",
                "description": "Due date/time string (e.g. 'tomorrow at 6 PM', '2026-10-02 18:00')."
            },
            "estimated_duration": {
                "type": "integer",
                "description": "Estimated duration in minutes (e.g. 45)."
            },
            "category": {
                "type": "string",
                "description": "Task category (e.g. 'Study', 'Engineering', 'Hackathon')."
            },
            "search": {
                "type": "string",
                "description": "Search keyword for listing tasks."
            }
        },
        "required": ["action"]
    }

    def check_requires_confirmation(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        action = params.get("action", "").lower()
        if action == "delete":
            task_id = params.get("task_id")
            return True, f"Permanently delete task #{task_id}? This action cannot be undone."
        return False, None

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        action = kwargs.get("action", "").lower()

        try:
            if action == "create":
                title = kwargs.get("title")
                if not title:
                    return ToolResult(success=False, error="Title is required to create a task.", message="Missing title")

                priority = kwargs.get("priority", "MEDIUM")
                due_date = kwargs.get("due_date")
                desc = kwargs.get("description", "")
                category = kwargs.get("category", "General")
                est_dur = int(kwargs.get("estimated_duration", 30))
                source = kwargs.get("source", "agent")

                task = TaskRepository.create(
                    conn=conn,
                    user_id=user_id,
                    title=title,
                    description=desc,
                    priority=priority,
                    due_date=due_date,
                    estimated_duration=est_dur,
                    category=category,
                    source=source
                )
                return ToolResult(
                    success=True,
                    data=task,
                    message=f"Created task #{task['id']}: '{task['title']}' with priority {task['priority']}."
                )

            elif action == "list":
                status = kwargs.get("status")
                priority = kwargs.get("priority")
                category = kwargs.get("category")
                search = kwargs.get("search")

                tasks = TaskRepository.list_all(
                    conn=conn,
                    user_id=user_id,
                    status=status,
                    priority=priority,
                    category=category,
                    search=search
                )
                return ToolResult(
                    success=True,
                    data=tasks,
                    message=f"Retrieved {len(tasks)} tasks."
                )

            elif action == "complete":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required to complete a task.")
                task = TaskRepository.complete(conn, int(task_id), user_id)
                if not task:
                    return ToolResult(success=False, error=f"Task #{task_id} not found.")
                return ToolResult(
                    success=True,
                    data=task,
                    message=f"Completed task #{task_id}: '{task['title']}'."
                )

            elif action == "update":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required to update a task.")

                updates = {}
                for key in ["title", "description", "priority", "status", "due_date", "estimated_duration", "category"]:
                    if key in kwargs and kwargs[key] is not None:
                        updates[key] = kwargs[key]

                task = TaskRepository.update(conn, int(task_id), user_id, **updates)
                if not task:
                    return ToolResult(success=False, error=f"Task #{task_id} not found.")
                return ToolResult(
                    success=True,
                    data=task,
                    message=f"Updated task #{task_id}: '{task['title']}'."
                )

            elif action == "delete":
                task_id = kwargs.get("task_id")
                if not task_id:
                    return ToolResult(success=False, error="task_id is required to delete a task.")
                deleted = TaskRepository.delete(conn, int(task_id), user_id)
                if not deleted:
                    return ToolResult(success=False, error=f"Task #{task_id} not found or already deleted.")
                return ToolResult(
                    success=True,
                    data={"task_id": task_id, "deleted": True},
                    message=f"Successfully deleted task #{task_id}."
                )

            else:
                return ToolResult(success=False, error=f"Unknown task action: '{action}'.")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"TaskTool execution failed: {str(e)}")
