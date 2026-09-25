import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "tasks.json"
)


def _normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure older tasks without newer fields are normalized."""
    if "status" not in task:
        task["status"] = "completed" if task.get("completed", False) else "pending"
    if "completed" not in task:
        task["completed"] = task.get("status") == "completed"
    if "due_date" not in task:
        task["due_date"] = None
    if "priority" not in task:
        task["priority"] = "medium"
    return task


def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from JSON storage."""
    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            raw = json.load(file)
            if isinstance(raw, list):
                return [_normalize_task(t) for t in raw]
            return []
    except Exception:
        return []


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Save tasks to JSON storage."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=2, ensure_ascii=False)


def get_tasks(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all tasks, optionally filtered by status ('pending' or 'completed')."""
    tasks = load_tasks()
    if status:
        status_clean = status.strip().lower()
        if status_clean in ("pending", "completed"):
            return [t for t in tasks if t.get("status") == status_clean]
    return tasks


def create_task(title: str, priority: str = "medium", due_date: Optional[str] = None) -> Dict[str, Any]:
    """Create a new task with title, priority, and optional due date/time."""
    tasks = load_tasks()

    if tasks:
        next_id = max(task["id"] for task in tasks) + 1
    else:
        next_id = 1

    clean_priority = priority.strip().lower() if priority else "medium"
    if clean_priority not in ("low", "medium", "high"):
        clean_priority = "medium"

    clean_due = due_date.strip() if due_date and isinstance(due_date, str) else None

    task = {
        "id": next_id,
        "title": title.strip(),
        "priority": clean_priority,
        "status": "pending",
        "completed": False,
        "due_date": clean_due,
        "created_at": datetime.now().isoformat()
    }

    tasks.append(task)
    save_tasks(tasks)
    return task


def complete_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Mark a task as completed by its ID."""
    tasks = load_tasks()

    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            task["status"] = "completed"
            task["completed_at"] = datetime.now().isoformat()
            save_tasks(tasks)
            return task

    return None


def delete_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Delete a task by its ID."""
    tasks = load_tasks()
    target_idx = None
    target_task = None

    for idx, task in enumerate(tasks):
        if task["id"] == task_id:
            target_idx = idx
            target_task = task
            break

    if target_idx is not None:
        deleted = tasks.pop(target_idx)
        save_tasks(tasks)
        return deleted

    return None


def clear_all_tasks() -> int:
    """Clear all tasks and return count of deleted items."""
    tasks = load_tasks()
    count = len(tasks)
    save_tasks([])
    return count