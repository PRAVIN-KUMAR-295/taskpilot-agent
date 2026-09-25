import sys
from pathlib import Path
from typing import Optional, Dict, Any, List

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.task_service import (
    get_tasks,
    create_task,
    complete_task,
    delete_task,
    clear_all_tasks
)
from services.search_service import (
    search_information
)

# Registry of risky actions requiring human confirmation before execution
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
    """Check if an action is marked as risky requiring confirmation."""
    return tool_name in RISKY_ACTIONS


def tool_get_tasks(status: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve all tasks or tasks filtered by status ('pending' or 'completed')."""
    tasks = get_tasks(status)
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
    """Create a new task with title, priority, and optional due date/time."""
    if not title or not title.strip():
        return {
            "success": False,
            "error": "Task title cannot be empty."
        }
    task = create_task(title=title, priority=priority, due_date=due_date)
    return {
        "success": True,
        "task": task,
        "message": f"Task #{task['id']} ('{task['title']}') created successfully."
    }


def tool_complete_task(task_id: int) -> Dict[str, Any]:
    """Mark a task as completed by its ID."""
    try:
        t_id = int(task_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": f"Invalid task_id: {task_id}. Must be an integer."
        }

    task = complete_task(t_id)
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
    """Permanently delete a task by its ID."""
    try:
        t_id = int(task_id)
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": f"Invalid task_id: {task_id}. Must be an integer."
        }

    task = delete_task(t_id)
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
    """Delete all tasks."""
    count = clear_all_tasks()
    return {
        "success": True,
        "cleared_count": count,
        "message": f"All {count} tasks have been cleared."
    }


def tool_search(query: str) -> Dict[str, Any]:
    """Search for information via Wikipedia public API."""
    return search_information(query)