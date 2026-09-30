import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_task_crud_rest_endpoints():
    # 1. Create Task
    create_res = client.post("/api/tasks", json={
        "title": "Configure AWS DynamoDB Migration Schema",
        "description": "Prepare NoSQL table definitions and primary partition keys",
        "priority": "HIGH",
        "status": "TODO",
        "due_date": "2026-10-05 18:00",
        "estimated_duration": 60,
        "category": "Cloud"
    })
    assert create_res.status_code == 200
    created = create_res.json()["task"]
    task_id = created["id"]
    assert created["title"] == "Configure AWS DynamoDB Migration Schema"
    assert created["priority"] == "HIGH"
    assert created["status"] == "TODO"

    # 2. Get Task
    get_res = client.get(f"/api/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["task"]["id"] == task_id

    # 3. Update Task
    patch_res = client.patch(f"/api/tasks/{task_id}", json={
        "priority": "URGENT",
        "status": "IN_PROGRESS",
        "estimated_duration": 90
    })
    assert patch_res.status_code == 200
    updated = patch_res.json()["task"]
    assert updated["priority"] == "URGENT"
    assert updated["status"] == "IN_PROGRESS"
    assert updated["estimated_duration"] == 90

    # 4. Complete Task
    comp_res = client.post(f"/api/tasks/{task_id}/complete")
    assert comp_res.status_code == 200
    assert comp_res.json()["task"]["status"] == "COMPLETED"

    # 5. List with Filter
    list_res = client.get("/api/tasks?category=Cloud")
    assert list_res.status_code == 200
    assert any(t["id"] == task_id for t in list_res.json()["tasks"])

    # 6. Delete Task
    del_res = client.delete(f"/api/tasks/{task_id}")
    assert del_res.status_code == 200

    # Verify 404
    not_found = client.get(f"/api/tasks/{task_id}")
    assert not_found.status_code == 404


def test_task_ai_actions():
    # Create test task
    t_res = client.post("/api/tasks", json={
        "title": "Prepare Pitch Presentation for Judges",
        "priority": "MEDIUM",
        "category": "Hackathon"
    })
    t_id = t_res.json()["task"]["id"]

    # AI Prioritize
    prio_res = client.post(f"/api/tasks/{t_id}/ai-action", json={"action": "prioritize"})
    assert prio_res.status_code == 200
    assert prio_res.json()["task"]["priority"] == "URGENT"

    # AI Explain Importance
    exp_res = client.post(f"/api/tasks/{t_id}/ai-action", json={"action": "explain"})
    assert exp_res.status_code == 200
    assert "essential" in exp_res.json()["explanation"].lower() or "prepare" in exp_res.json()["explanation"].lower()

    # AI Break into subtasks
    sub_res = client.post(f"/api/tasks/{t_id}/ai-action", json={"action": "subtasks"})
    assert sub_res.status_code == 200
    assert len(sub_res.json()["created_subtasks"]) == 3
