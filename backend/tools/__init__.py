from typing import Optional, Dict, Any, List
from .base import BaseTool, ToolResult
from .registry import ToolRegistry, default_registry
from .task_tool import TaskTool
from .reminder_tool import ReminderTool
from .schedule_tool import ScheduleTool
from .planning_tool import PlanningTool
from .search_tool import SearchKnowledgeTool
from .notification_tool import NotificationTool

# Legacy compatibility imports for tests
try:
    from services.task_service import (
        get_tasks as _get_tasks,
        create_task as _create_task,
        complete_task as _complete_task,
        delete_task as _delete_task,
        clear_all_tasks as _clear_all_tasks
    )
    from services.search_service import search_information as _search_info
except ImportError:
    from backend.services.task_service import (
        get_tasks as _get_tasks,
        create_task as _create_task,
        complete_task as _complete_task,
        delete_task as _delete_task,
        clear_all_tasks as _clear_all_tasks
    )
    from backend.services.search_service import search_information as _search_info

RISKY_ACTIONS = {
    "delete_task": {
        "description": "Permanently delete a task by ID",
        "warning": "This will permanently remove the task from storage."
    },
    "clear_all_tasks": {
        "description": "Delete all stored tasks",
        "warning": "This will permanently delete all tasks in the system."
    }
}


def is_risky_action(tool_name: str) -> bool:
    return tool_name in RISKY_ACTIONS


def tool_get_tasks(status: Optional[str] = None) -> Dict[str, Any]:
    tasks = _get_tasks(status)
    return {
        "success": True,
        "count": len(tasks),
        "status_filter": status,
        "tasks": tasks
    }


def tool_create_task(
    title: str,
    priority: str = "medium",
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    if not title or not title.strip():
        return {
            "success": False,
            "error": "Task title cannot be empty."
        }
    task = _create_task(title=title, priority=priority, due_date=due_date)
    return {
        "success": True,
        "task": task,
        "message": f"Task #{task['id']} ('{task['title']}') created successfully."
    }


def tool_complete_task(task_id: int) -> Dict[str, Any]:
    try:
        t_id = int(task_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": f"Invalid task_id: {task_id}. Must be an integer."
        }

    task = _complete_task(t_id)
    if task is None:
        return {
            "success": False,
            "message": f"Task #{t_id} not found."
        }

    return {
        "success": True,
        "task": task,
        "message": f"Task #{t_id} ('{task['title']}') marked as completed."
    }


def tool_delete_task(task_id: int) -> Dict[str, Any]:
    try:
        t_id = int(task_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": f"Invalid task_id: {task_id}. Must be an integer."
        }

    task = _delete_task(t_id)
    if task is None:
        return {
            "success": False,
            "message": f"Task #{t_id} not found."
        }

    return {
        "success": True,
        "deleted_task": task,
        "message": f"Task #{t_id} ('{task['title']}') deleted permanently."
    }


def tool_clear_all_tasks() -> Dict[str, Any]:
    count = _clear_all_tasks()
    return {
        "success": True,
        "cleared_count": count,
        "message": f"All {count} tasks have been cleared."
    }


def tool_search(query: str) -> Dict[str, Any]:
    return _search_info(query)


__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "default_registry",
    "TaskTool",
    "ReminderTool",
    "ScheduleTool",
    "PlanningTool",
    "SearchKnowledgeTool",
    "NotificationTool",
    # Legacy compatibility exports
    "tool_get_tasks",
    "tool_create_task",
    "tool_complete_task",
    "tool_delete_task",
    "tool_clear_all_tasks",
    "tool_search",
    "is_risky_action",
    "RISKY_ACTIONS"
]
