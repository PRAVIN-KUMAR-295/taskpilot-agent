import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.connection import get_db_connection
from backend.database.repositories import MemoryRepository, ScheduleRepository

client = TestClient(app)


def test_memory_crud_endpoints():
    # 1. Create memory
    post_res = client.post("/api/memory", json={
        "key": "preferred_study_duration",
        "value": "50 minutes focus + 10 minutes break",
        "category": "habit"
    })
    assert post_res.status_code == 200
    mem = post_res.json()["memory"]
    mem_id = mem["id"]
    assert mem["key"] == "preferred_study_duration"

    # 2. Get memories
    get_res = client.get("/api/memory")
    assert get_res.status_code == 200
    mems = get_res.json()["memories"]
    assert any(m["id"] == mem_id for m in mems)

    # 3. Delete memory
    del_res = client.delete(f"/api/memory/{mem_id}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_schedule_and_optimization_endpoints():
    # 1. Create schedule block
    sch_res = client.post("/api/calendar", json={
        "title": "AWS CloudFront & Edge Optimization Sprint",
        "start_time": "10:00 AM",
        "end_time": "11:30 AM",
        "day_of_week": "Today",
        "session_type": "focus"
    })
    assert sch_res.status_code == 200
    sch = sch_res.json()["schedule"]
    assert sch["title"] == "AWS CloudFront & Edge Optimization Sprint"

    # 2. Optimize schedule endpoint
    opt_res = client.post("/api/agent/optimize-schedule")
    assert opt_res.status_code == 200
    opt_data = opt_res.json()
    assert opt_data["success"] is True
    assert "optimized" in opt_data["message"].lower()

    # 3. Get calendar overview
    cal_res = client.get("/api/calendar")
    assert cal_res.status_code == 200
    cal_data = cal_res.json()
    assert "schedules" in cal_data
    assert "reminders" in cal_data
    assert "tasks" in cal_data


def test_agent_audit_actions_log():
    # Fetch recent audit actions
    res = client.get("/api/agent/actions?limit=10")
    assert res.status_code == 200
    actions = res.json()["actions"]
    assert isinstance(actions, list)
    if actions:
        act = actions[0]
        assert "tool_name" in act
        assert "status" in act
        assert "verification_status" in act
