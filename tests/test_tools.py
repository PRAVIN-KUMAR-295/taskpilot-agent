import sys
from pathlib import Path

# Add project root and backend to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
for path in [str(root_dir), str(backend_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest
from backend.services.task_service import clear_all_tasks
from backend.tools import (
    tool_get_tasks,
    tool_create_task,
    tool_complete_task,
    tool_delete_task,
    tool_clear_all_tasks,
    tool_search,
    is_risky_action
)
from backend.services.memory_service import (
    save_memory,
    get_recent_memory,
    scrub_secrets,
    clear_memory
)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean tasks and memory for each test."""
    clear_all_tasks()
    clear_memory()
    yield
    clear_all_tasks()
    clear_memory()


def test_task_creation_with_due_date_and_priority():
    """Test creating a task with title, priority, and optional due date."""
    res = tool_create_task(
        title="Prepare hackathon pitch",
        priority="high",
        due_date="tomorrow at 10am"
    )

    assert res["success"] is True
    task = res["task"]
    assert task["id"] == 1
    assert task["title"] == "Prepare hackathon pitch"
    assert task["priority"] == "high"
    assert task["due_date"] == "tomorrow at 10am"
    assert task["status"] == "pending"
    assert task["completed"] is False


def test_task_creation_validation():
    """Test that empty titles are rejected gracefully."""
    res = tool_create_task(title="", priority="low")
    assert res["success"] is False
    assert "cannot be empty" in res["error"]


def test_task_listing_and_filtering():
    """Test listing tasks and filtering by status."""
    tool_create_task(title="Task One", priority="low")
    task2_res = tool_create_task(title="Task Two", priority="high")
    tool_complete_task(task2_res["task"]["id"])

    # All tasks
    all_res = tool_get_tasks()
    assert all_res["count"] == 2

    # Pending tasks only
    pending_res = tool_get_tasks(status="pending")
    assert pending_res["count"] == 1
    assert pending_res["tasks"][0]["title"] == "Task One"

    # Completed tasks only
    completed_res = tool_get_tasks(status="completed")
    assert completed_res["count"] == 1
    assert completed_res["tasks"][0]["title"] == "Task Two"


def test_task_completion():
    """Test marking an existing task complete."""
    created = tool_create_task(title="Submit documentation")
    task_id = created["task"]["id"]

    complete_res = tool_complete_task(task_id)
    assert complete_res["success"] is True
    assert complete_res["task"]["status"] == "completed"
    assert complete_res["task"]["completed"] is True

    # Complete non-existent task
    not_found = tool_complete_task(9999)
    assert not_found["success"] is False


def test_risky_action_detection_and_deletion():
    """Test deletion and risky action identification."""
    assert is_risky_action("delete_task") is True
    assert is_risky_action("clear_all_tasks") is True
    assert is_risky_action("create_task") is False

    t = tool_create_task(title="Temporary task")
    t_id = t["task"]["id"]

    del_res = tool_delete_task(t_id)
    assert del_res["success"] is True
    assert del_res["deleted_task"]["id"] == t_id

    # Verify task is gone
    list_after = tool_get_tasks()
    assert list_after["count"] == 0


def test_real_search_service():
    """Test live search service against Wikipedia."""
    res = tool_search("Python programming language")
    assert res["success"] is True
    assert "Python" in res["query"]
    assert len(res["results"]) > 0
    assert "title" in res["results"][0]
    assert "url" in res["results"][0]
    assert "wikipedia.org" in res["results"][0]["url"]


def test_search_service_empty_query():
    """Test search failure handling on empty input."""
    res = tool_search("")
    assert res["success"] is False
    assert "cannot be empty" in res["error"]


def test_memory_service_secret_scrubbing():
    """Test that API keys and sensitive tokens are masked before storage."""
    secret_text = "Here is my secret sk-proj-1234567890abcdef1234567890 and Bearer 9876543210abcdef9876543210"
    scrubbed = scrub_secrets(secret_text)

    assert "sk-proj" not in scrubbed
    assert "Bearer" not in scrubbed
    assert "[REDACTED_SECRET]" in scrubbed

    save_memory(secret_text, "Assistant response")
    memories = get_recent_memory()
    assert len(memories) == 1
    assert "sk-proj" not in memories[0]["user"]