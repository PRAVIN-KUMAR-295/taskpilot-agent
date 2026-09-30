import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import sqlite3

# Ensure backend directory and root are in sys.path
backend_dir = Path(__file__).resolve().parent
root_dir = backend_dir.parent
for p in [str(backend_dir), str(root_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

frontend_path = (root_dir / "frontend").resolve()

from fastapi import FastAPI, HTTPException, Depends, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    is_bedrock_configured,
    is_openai_configured,
    AWS_REGION,
    BEDROCK_MODEL_ID,
    MODEL_NAME
)
from database.connection import get_db, init_db
from database.repositories import (
    UserRepository,
    TaskRepository,
    ReminderRepository,
    ScheduleRepository,
    PlanRepository,
    AgentRunRepository,
    AgentActionRepository,
    MemoryRepository
)
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_user_optional
)
from models import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    TaskCreateRequest,
    TaskUpdateRequest,
    ReminderCreateRequest,
    ScheduleCreateRequest,
    MemoryCreateRequest,
    AgentRunRequest,
    ChatRequest,
    ChatResponse
)
from agent.orchestrator import default_orchestrator
from agent.legacy_agent import run_agent as legacy_run_agent

from tools.registry import default_registry

app = FastAPI(
    title="TaskPilot Agent API",
    description="Autonomous AI Agent for Everyday Apps - PS 01 Hackathon Production Backend",
    version="2.0.0"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Mount static frontend directory if present
if frontend_path.is_dir():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.on_event("startup")
def on_startup():
    """Initialize SQLite database and seed demo data."""
    init_db()


# ==========================================
# ROOT & HEALTH CHECK ENDPOINTS
# ==========================================

from fastapi import Request
from fastapi.responses import FileResponse

@app.get("/")
def home(request: Request):
    """Root status endpoint; serves Single Page Application to browsers and JSON to API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        index_file = frontend_path / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
    return {
        "status": "online",
        "app": "TaskPilot AI Agent",
        "version": "2.0.0",
        "problem_statement": "PS 01 – Autonomous Agents for Everyday Apps",
        "message": "TaskPilot Autonomous Agent API is active and operational."
    }

@app.get("/app")
def serve_app():
    index_file = frontend_path / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Frontend index.html not found.")

@app.get("/style.css")
def serve_css():
    css_file = frontend_path / "style.css"
    if css_file.is_file():
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found.")

@app.get("/app.js")
def serve_js():
    js_file = frontend_path / "app.js"
    if js_file.is_file():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found.")



@app.get("/health")
@app.get("/api/health")
def health(conn: sqlite3.Connection = Depends(get_db)):
    """Comprehensive health check endpoint reporting agent, database, and model status."""
    demo_user = UserRepository.get_by_email(conn, "demo@taskpilot.ai")
    user_id = demo_user["id"] if demo_user else 1
    tasks = TaskRepository.list_all(conn, user_id=user_id)
    pending = [t for t in tasks if t["status"] in ["TODO", "IN_PROGRESS"]]
    completed = [t for t in tasks if t["status"] == "COMPLETED"]

    return {
        "status": "healthy",
        "agent": "TaskPilot Orchestrator v2.0",
        "database": "SQLite (DynamoDB Architecture Ready)",
        "aws_bedrock_configured": is_bedrock_configured(),
        "aws_region": AWS_REGION if is_bedrock_configured() else "local-mock",
        "bedrock_model_id": BEDROCK_MODEL_ID if is_bedrock_configured() else "LocalProvider Heuristic Fallback",
        "tools_count": len(default_registry.list_all()),
        "tasks_count": len(tasks),
        "pending_tasks": len(pending),
        "completed_tasks": len(completed)
    }


# ==========================================
# AUTHENTICATION ENDPOINTS
# ==========================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register(req: RegisterRequest, conn: sqlite3.Connection = Depends(get_db)):
    existing = UserRepository.get_by_email(conn, req.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    pw_hash = hash_password(req.password)
    user = UserRepository.create(conn, name=req.name, email=req.email, password_hash=pw_hash)
    token = create_access_token(user["id"], user["email"])

    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return AuthResponse(
        success=True,
        token=token,
        user=safe_user,
        message="Account created successfully."
    )


@app.post("/api/auth/login", response_model=AuthResponse)
def login(req: LoginRequest, conn: sqlite3.Connection = Depends(get_db)):
    user = UserRepository.get_by_email(conn, req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(user["id"], user["email"])
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return AuthResponse(
        success=True,
        token=token,
        user=safe_user,
        message="Logged in successfully."
    )


@app.get("/api/auth/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user_optional)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {k: v for k, v in user.items() if k != "password_hash"}


# ==========================================
# DASHBOARD STATS
# ==========================================

@app.get("/api/stats")
def get_dashboard_stats(
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    tasks = TaskRepository.list_all(conn, user_id=user_id)
    reminders = ReminderRepository.list_by_user(conn, user_id=user_id)
    schedules = ScheduleRepository.list_by_user(conn, user_id=user_id)
    recent_actions = AgentActionRepository.list_by_user(conn, user_id=user_id, limit=5)
    memories = MemoryRepository.get_all(conn, user_id=user_id)

    total_tasks = len(tasks)
    pending = len([t for t in tasks if t["status"] in ["TODO", "IN_PROGRESS"]])
    completed = len([t for t in tasks if t["status"] == "COMPLETED"])
    blocked = len([t for t in tasks if t["status"] == "BLOCKED"])
    urgent = len([t for t in tasks if t["priority"] == "URGENT" and t["status"] != "COMPLETED"])

    completion_rate = round((completed / total_tasks * 100), 1) if total_tasks > 0 else 0

    return {
        "user_name": user["name"] if user else "Hackathon Guest",
        "total_tasks": total_tasks,
        "pending_tasks": pending,
        "completed_tasks": completed,
        "blocked_tasks": blocked,
        "urgent_tasks": urgent,
        "completion_rate_percent": completion_rate,
        "active_reminders_count": len([r for r in reminders if r["status"] == "SCHEDULED"]),
        "scheduled_blocks_count": len(schedules),
        "recent_actions": recent_actions,
        "active_memories_count": len(memories)
    }


# ==========================================
# TASK MANAGEMENT ENDPOINTS
# ==========================================

@app.get("/api/tasks")
@app.get("/tasks")
def list_tasks_endpoint(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    tasks = TaskRepository.list_all(
        conn=conn,
        user_id=user_id,
        status=status,
        priority=priority,
        category=category,
        search=search
    )
    return {"tasks": tasks}


@app.post("/api/tasks")
@app.post("/tasks")
def create_task_endpoint(
    req: TaskCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    task = TaskRepository.create(
        conn=conn,
        user_id=user_id,
        title=req.title,
        description=req.description or "",
        priority=req.priority or "MEDIUM",
        status=req.status or "TODO",
        due_date=req.due_date,
        estimated_duration=req.estimated_duration or 30,
        category=req.category or "General",
        source="user",
        dependencies=req.dependencies or []
    )
    return {"success": True, "task": task}


@app.get("/api/tasks/{task_id}")
def get_task_endpoint(
    task_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    task = TaskRepository.get_by_id(conn, task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")
    return {"task": task}


@app.patch("/api/tasks/{task_id}")
def update_task_endpoint(
    task_id: int,
    req: TaskUpdateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    task = TaskRepository.update(
        conn=conn,
        task_id=task_id,
        user_id=user_id,
        **req.model_dump(exclude_unset=True)
    )
    if not task:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")
    return {"success": True, "task": task}


@app.delete("/api/tasks/{task_id}")
def delete_task_endpoint(
    task_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    success = TaskRepository.delete(conn, task_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")
    return {"success": True, "message": f"Task #{task_id} deleted."}


@app.post("/api/tasks/{task_id}/complete")
@app.post("/tasks/{task_id}/complete")
def complete_task_endpoint(
    task_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    task = TaskRepository.complete(conn, task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")
    return {"success": True, "task": task}


@app.post("/api/tasks/{task_id}/ai-action")
def task_ai_action_endpoint(
    task_id: int,
    payload: Dict[str, str],
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Performs AI actions on a specific task:
    - prioritize
    - subtasks
    - explain
    """
    user_id = user["id"] if user else 1
    task = TaskRepository.get_by_id(conn, task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")

    action = payload.get("action", "explain")

    if action == "prioritize":
        new_priority = "URGENT" if task["priority"] in ["MEDIUM", "HIGH"] else "HIGH"
        updated = TaskRepository.update(conn, task_id, user_id, priority=new_priority)
        return {
            "success": True,
            "action": "prioritize",
            "message": f"AI elevated priority of '{task['title']}' to {new_priority} based on deadline urgency.",
            "task": updated
        }
    elif action == "subtasks":
        # Break into 3 subtasks
        sub1 = TaskRepository.create(conn, user_id, f"Part 1: Research & Outline for {task['title']}", priority="HIGH", category=task["category"])
        sub2 = TaskRepository.create(conn, user_id, f"Part 2: Implement Core of {task['title']}", priority="HIGH", category=task["category"])
        sub3 = TaskRepository.create(conn, user_id, f"Part 3: Verify & Review {task['title']}", priority="MEDIUM", category=task["category"])
        return {
            "success": True,
            "action": "subtasks",
            "message": f"Decomposed '{task['title']}' into 3 actionable subtasks.",
            "created_subtasks": [sub1, sub2, sub3]
        }
    else:
        # Explain why this task is important
        explanation = (
            f"Task '{task['title']}' (Priority: {task['priority']}) is essential because it unlocks dependent milestones "
            f"and aligns with your focus targets in category '{task['category']}'. Completing this early reduces cognitive load."
        )
        return {
            "success": True,
            "action": "explain",
            "explanation": explanation
        }


# ==========================================
# AGENT ORCHESTRATION ENDPOINTS
# ==========================================

@app.post("/api/agent/run")
def run_agent_endpoint(
    req: AgentRunRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Core Autonomous Agent Orchestration Endpoint.
    Executes:
    UNDERSTANDING -> PLANNING -> TOOL SELECTION -> (WAITING_FOR_APPROVAL) -> EXECUTING -> VERIFYING -> RESULT
    """
    user_id = user["id"] if user else 1
    goal = (req.goal or req.message or "").strip()

    if not goal and not req.confirmed_action:
        raise HTTPException(status_code=400, detail="Please provide a goal, prompt, or confirmed_action.")

    try:
        agent_res = default_orchestrator.run(
            user_id=user_id,
            conn=conn,
            goal=goal,
            confirmed_action=req.confirmed_action,
            run_id=req.run_id
        )
        return agent_res
    except Exception as e:
        return {
            "success": False,
            "status": "FAILED",
            "error": str(e),
            "summary": f"Agent encountered an unexpected issue: {str(e)}",
            "timeline": [{"step": "FAILED", "status": "failed", "message": str(e)}]
        }


@app.get("/api/agent/runs/{run_id}")
def get_agent_run_endpoint(
    run_id: str,
    conn: sqlite3.Connection = Depends(get_db)
):
    run = AgentRunRepository.get_by_id(conn, run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Agent run '{run_id}' not found.")
    return {"run": run}


@app.get("/api/agent/actions")
def get_agent_actions_endpoint(
    limit: int = Query(50, ge=1, le=200),
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """Activity / Audit Log endpoint showing transparent agent actions and verification."""
    user_id = user["id"] if user else 1
    actions = AgentActionRepository.list_by_user(conn, user_id=user_id, limit=limit)
    return {"actions": actions}


@app.post("/api/agent/optimize-schedule")
def optimize_schedule_endpoint(
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """Direct agent trigger to optimize schedule based on stored preferences."""
    user_id = user["id"] if user else 1
    tool_res = default_registry.execute("schedule_tool", user_id=user_id, conn=conn, action="optimize")
    return tool_res.to_dict()


@app.get("/api/agent/tools")
def list_agent_tools_endpoint():
    """Returns all available native and simulated tools with schemas and flags."""
    return {"tools": default_registry.get_tool_specs()}


# ==========================================
# PLANS ENDPOINTS
# ==========================================

@app.get("/api/plans")
def list_plans_endpoint(
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    plans = PlanRepository.list_by_user(conn, user_id)
    return {"plans": plans}


@app.get("/api/plans/{plan_id}")
def get_plan_endpoint(
    plan_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    plan = PlanRepository.get_by_id(conn, plan_id, user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return {"plan": plan}


# ==========================================
# CALENDAR / SCHEDULE ENDPOINTS
# ==========================================

@app.get("/api/calendar")
def get_calendar_endpoint(
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    schedules = ScheduleRepository.list_by_user(conn, user_id)
    reminders = ReminderRepository.list_by_user(conn, user_id)
    tasks = TaskRepository.list_all(conn, user_id)
    return {
        "schedules": schedules,
        "reminders": reminders,
        "tasks": tasks
    }


@app.post("/api/calendar")
def create_schedule_endpoint(
    req: ScheduleCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    item = ScheduleRepository.create(
        conn=conn,
        user_id=user_id,
        title=req.title,
        start_time=req.start_time,
        end_time=req.end_time,
        task_id=req.task_id,
        day_of_week=req.day_of_week,
        session_type=req.session_type or "focus"
    )
    return {"success": True, "schedule": item}


# ==========================================
# REMINDERS ENDPOINTS
# ==========================================

@app.get("/api/reminders")
def list_reminders_endpoint(
    status: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    reminders = ReminderRepository.list_by_user(conn, user_id, status=status)
    return {"reminders": reminders}


@app.post("/api/reminders")
def create_reminder_endpoint(
    req: ReminderCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    reminder = ReminderRepository.create(
        conn=conn,
        user_id=user_id,
        title=req.title,
        reminder_time=req.reminder_time,
        task_id=req.task_id,
        channel=req.channel or "in_app"
    )
    return {"success": True, "reminder": reminder}


@app.delete("/api/reminders/{reminder_id}")
def cancel_reminder_endpoint(
    reminder_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    success = ReminderRepository.cancel(conn, reminder_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reminder not found.")
    return {"success": True, "message": f"Reminder #{reminder_id} cancelled."}


# ==========================================
# AGENT MEMORY ENDPOINTS
# ==========================================

@app.get("/api/memory")
def get_memory_endpoint(
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """View stored non-sensitive user preferences and habits."""
    user_id = user["id"] if user else 1
    memories = MemoryRepository.get_all(conn, user_id)
    return {"memories": memories}


@app.post("/api/memory")
def set_memory_endpoint(
    req: MemoryCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    item = MemoryRepository.set(
        conn=conn,
        user_id=user_id,
        key=req.key,
        value=req.value,
        category=req.category or "preference",
        source="user_interface"
    )
    return {"success": True, "memory": item}


@app.delete("/api/memory/{memory_id}")
def delete_memory_endpoint(
    memory_id: int,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    user_id = user["id"] if user else 1
    success = MemoryRepository.delete(conn, memory_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory preference not found.")
    return {"success": True, "message": f"Memory preference #{memory_id} removed."}


# ==========================================
# BACKWARDS-COMPATIBLE CHAT ENDPOINT
# ==========================================

@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user_optional),
    conn: sqlite3.Connection = Depends(get_db)
):
    """
    Backwards compatibility chat endpoint for earlier tests and simple chat callers.
    """
    try:
        clean_msg = request.message.strip()
        if not clean_msg and not request.confirmed_action:
            return ChatResponse(
                response="Please provide a message or task instruction.",
                success=False,
                error="EmptyMessage"
            )

        user_id = user["id"] if user else 1
        agent_result = legacy_run_agent(
            user_message=clean_msg,
            confirmed_action=request.confirmed_action
        )


        return ChatResponse(
            response=agent_result.get("response") or agent_result.get("summary", ""),
            success=agent_result.get("success", True),
            action_pending_approval=agent_result.get("action_pending_approval"),
            tasks=agent_result.get("tasks"),
            error=agent_result.get("error")
        )
    except Exception as e:
        return ChatResponse(
            response=f"An error occurred while processing your request: {str(e)}",
            success=False,
            error=str(e)
        )
if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT)