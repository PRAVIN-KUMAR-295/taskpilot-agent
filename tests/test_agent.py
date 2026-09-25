import sys
from pathlib import Path

# Add project root and backend to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
for path in [str(root_dir), str(backend_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.task_service import clear_all_tasks
from backend.services.memory_service import clear_memory
from backend.agent import run_agent


client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean tasks and memory for each test."""
    clear_all_tasks()
    clear_memory()
    yield
    clear_all_tasks()
    clear_memory()


def test_home_endpoint():
    """Verify GET / returns online status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "TaskPilot" in data["app"]


def test_health_endpoint():
    """Verify GET /health returns status and task counts."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "tasks_count" in data


def test_chat_invalid_empty_input():
    """Verify POST /chat rejects empty string."""
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False


def test_agent_task_creation_workflow():
    """Verify agent creates task with priority and due date from natural language."""
    res = run_agent("Create a task to build hackathon presentation tomorrow with high priority")
    assert res["success"] is True
    assert res["tasks"] is not None
    assert len(res["tasks"]) == 1

    created = res["tasks"][0]
    assert created["id"] == 1
    assert "presentation" in created["title"].lower()
    assert created["priority"] == "high"
    assert created["due_date"] is not None
    assert created["status"] == "pending"


def test_agent_task_listing_workflow():
    """Verify agent retrieves pending tasks accurately."""
    run_agent("Create a task to write tests")
    res = run_agent("Show me my pending tasks")

    assert res["success"] is True
    assert res["tasks"] is not None
    assert len(res["tasks"]) == 1
    assert "write tests" in res["response"]


def test_agent_task_completion_workflow():
    """Verify agent marks tasks complete."""
    run_agent("Create a task to submit demo")
    res = run_agent("Complete task #1")

    assert res["success"] is True
    assert res["tasks"] is not None
    assert res["tasks"][0]["status"] == "completed"
    assert res["tasks"][0]["completed"] is True


def test_human_approval_intercepts_risky_deletion():
    """Verify agent halts risky deletion and returns action_pending_approval."""
    run_agent("Create a task to test safety")

    # Attempt deletion without prior confirmation
    res = run_agent("Delete task 1")
    assert res["success"] is True
    assert res["action_pending_approval"] is not None

    approval = res["action_pending_approval"]
    assert approval["tool_name"] == "delete_task"
    assert approval["arguments"]["task_id"] == 1

    # Task should still exist before confirmation
    list_check = run_agent("Show pending tasks")
    assert len(list_check["tasks"]) == 1

    # Now execute with confirmation
    confirm_res = run_agent(
        "Confirm deletion",
        confirmed_action={"tool_name": "delete_task", "arguments": {"task_id": 1}}
    )
    assert confirm_res["success"] is True
    assert "deleted permanently" in confirm_res["response"]

    # Verify task is now deleted
    list_after = run_agent("Show pending tasks")
    assert list_after["tasks"] == []


def test_chat_endpoint_full_flow():
    """Verify POST /chat endpoint handles message and returns ChatResponse structure."""
    response = client.post("/chat", json={
        "message": "Create a task to verify frontend communication"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["response"] != ""
    assert data["tasks"] is not None
    assert len(data["tasks"]) == 1


def test_agent_handles_openai_auth_error(monkeypatch):
    """Verify agent gracefully handles 401 AuthenticationError without crashing."""
    import openai
    from unittest.mock import MagicMock
    import backend.agent as agent_mod

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = openai.AuthenticationError(
        "Invalid API Key",
        response=MagicMock(status_code=401),
        body={"error": {"message": "Invalid API key"}}
    )
    monkeypatch.setattr(agent_mod, "get_client", lambda: mock_client)

    res = agent_mod.run_agent("Hello agent")
    assert res["success"] is False
    assert "Authentication" in res["response"] or "401" in res["response"]


def test_agent_handles_openai_rate_limit_error(monkeypatch):
    """Verify agent gracefully handles 429 RateLimitError without crashing."""
    import openai
    from unittest.mock import MagicMock
    import backend.agent as agent_mod

    mock_client = MagicMock()
    mock_client.responses.create.side_effect = openai.RateLimitError(
        "You have no credits remaining",
        response=MagicMock(status_code=429),
        body={"error": {"code": "credit_balance_exhausted"}}
    )
    monkeypatch.setattr(agent_mod, "get_client", lambda: mock_client)

    # General conversation without local task command
    res = agent_mod.run_agent("Tell me a philosophy joke")
    assert "Quota Exhausted" in res["response"] or "credits" in res["response"]
    assert res["error"] == "RateLimitError"