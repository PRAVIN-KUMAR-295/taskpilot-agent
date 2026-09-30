import pytest
from backend.agent.intent_analyzer import IntentAnalyzer
from backend.agent.planner import TaskPlanner
from backend.agent.tool_selector import ToolSelector
from backend.agent.orchestrator import AgentOrchestrator
from backend.database.connection import get_db_connection
from backend.database.repositories import TaskRepository


def test_intent_analyzer_classification():
    conn = get_db_connection()
    analyzer = IntentAnalyzer()

    # Study plan intent
    res_study = analyzer.analyze(user_id=1, conn=conn, message="Create a 7-day study plan for AWS Solutions Architect exam")
    assert res_study["intent"] == "STUDY_PLAN"

    # Project plan intent
    res_proj = analyzer.analyze(user_id=1, conn=conn, message="Break down our hackathon submission and schedule deadlines")
    assert res_proj["intent"] == "PROJECT_PLAN"

    # Daily plan intent
    res_daily = analyzer.analyze(user_id=1, conn=conn, message="Plan my day and prioritize my tasks")
    assert res_daily["intent"] == "DAILY_PLAN"

    # Schedule optimize intent
    res_opt = analyzer.analyze(user_id=1, conn=conn, message="Optimize my schedule for peak evening focus")
    assert res_opt["intent"] == "SCHEDULE_OPTIMIZE"

    # Memory preference intent
    res_mem = analyzer.analyze(user_id=1, conn=conn, message="I prefer studying in the evening between 7 PM and 9 PM")
    assert res_mem["intent"] == "MEMORY_UPDATE"


def test_task_planner_structured_output():
    planner = TaskPlanner()
    intent_data = {"intent": "STUDY_PLAN"}
    memory_ctx = {"preferred_evening_focus": "07:00 PM - 09:00 PM"}

    plan = planner.plan(
        goal="Prepare for AWS Solutions Architect Associate exam",
        intent_data=intent_data,
        memory_context=memory_ctx
    )
    assert plan["total_tasks"] >= 5
    assert len(plan["tasks"]) >= 5
    for t in plan["tasks"]:
        assert "title" in t
        assert t["priority"] in ["LOW", "MEDIUM", "HIGH", "URGENT"]
        assert t["estimated_minutes"] > 0
        assert "day_or_stage" in t


def test_tool_selector_pipeline_and_safety():
    plan = {
        "title": "AWS Study Blueprint",
        "tasks": [
            {"title": "Day 1: Cloud Concepts", "priority": "HIGH", "estimated_minutes": 60, "day_or_stage": "Day 1"}
        ]
    }
    # Large plan requires approval card
    pipeline, req_app, app_act = ToolSelector.select_tools(
        intent="STUDY_PLAN",
        goal="Prepare for AWS exam",
        plan=plan,
        entities={}
    )
    assert req_app is True
    assert app_act["type"] == "APPROVE_PLAN"
    tools_selected = [p["tool_name"] for p in pipeline]
    assert "planning_tool" in tools_selected
    assert "task_tool" in tools_selected

    # Destructive action requires approval
    pipe_del, req_del, app_del = ToolSelector.select_tools(
        intent="TASK_ACTION",
        goal="Delete task 99",
        plan={},
        entities={"action": "delete", "task_id": 99}
    )
    assert req_del is True
    assert app_del["type"] == "DELETE_TASK"


def test_orchestrator_autonomous_plan_and_approval_flow():
    conn = get_db_connection()
    orch = AgentOrchestrator()

    # Step 1: Initial user goal triggers UNDERSTANDING -> PLANNING -> WAITING_FOR_APPROVAL
    run_res = orch.run(
        user_id=1,
        conn=conn,
        goal="Create a plan to finish my AWS project by Friday."
    )
    assert run_res["success"] is True
    assert run_res["status"] == "WAITING_FOR_APPROVAL"
    assert run_res["requiresApproval"] is True
    assert run_res["actionPendingApproval"] is not None
    assert len(run_res["plan"]["tasks"]) > 0

    # Verify timeline reflects the state transitions
    timeline_steps = [s["step"] for s in run_res["timeline"]]
    assert "UNDERSTANDING" in timeline_steps
    assert "PLANNING" in timeline_steps
    assert "TOOL_SELECTION" in timeline_steps
    assert "WAITING_FOR_APPROVAL" in timeline_steps

    # Step 2: User clicks [Approve Plan]
    approval_payload = run_res["actionPendingApproval"]
    confirm_res = orch.run(
        user_id=1,
        conn=conn,
        goal="Create a plan to finish my AWS project by Friday.",
        confirmed_action=approval_payload,
        run_id=run_res["run_id"]
    )
    assert confirm_res["success"] is True
    assert confirm_res["status"] == "COMPLETED"
    assert confirm_res["requiresApproval"] is False
    assert confirm_res["actionsExecuted"] > 0
    assert confirm_res["actionsSuccessful"] > 0

    confirm_timeline = [s["step"] for s in confirm_res["timeline"]]
    assert "EXECUTING" in confirm_timeline
    assert "VERIFYING" in confirm_timeline
    assert "COMPLETED" in confirm_timeline
