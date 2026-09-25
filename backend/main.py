import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    ChatRequest,
    ChatResponse,
    TaskCreateRequest,
    TaskItem
)
from agent import run_agent
from config import is_openai_configured, MODEL_NAME
from services.task_service import get_tasks, create_task, complete_task


app = FastAPI(
    title="TaskPilot AI Agent",
    description="Autonomous AI Agent for Everyday Apps - Build Fast with AI Challenge 2026",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
def home():
    """Root status endpoint."""
    return {
        "status": "online",
        "app": "TaskPilot AI Agent",
        "version": "1.0.0",
        "message": "TaskPilot AI Agent is running!"
    }


@app.get("/health")
def health():
    """Health check endpoint with system status."""
    tasks = get_tasks()
    return {
        "status": "healthy",
        "openai_configured": is_openai_configured(),
        "model": MODEL_NAME,
        "tasks_count": len(tasks),
        "pending_tasks": len([t for t in tasks if t.get("status") == "pending"])
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Passes user natural language message and optional pre-confirmed action to agent.
    Never crashes with unhandled 500.
    """
    try:
        clean_msg = request.message.strip()
        if not clean_msg:
            return ChatResponse(
                response="Please provide a message or task instruction.",
                success=False,
                error="EmptyMessage"
            )

        agent_result = run_agent(
            user_message=clean_msg,
            confirmed_action=request.confirmed_action
        )

        return ChatResponse(
            response=agent_result.get("response", ""),
            success=agent_result.get("success", True),
            action_pending_approval=agent_result.get("action_pending_approval"),
            tasks=agent_result.get("tasks"),
            error=agent_result.get("error")
        )

    except Exception as e:
        # Graceful error response instead of 500 crash
        return ChatResponse(
            response=f"An error occurred while processing your request: {str(e)}",
            success=False,
            error=str(e)
        )


@app.get("/tasks")
def list_tasks_endpoint(status: Optional[str] = None):
    """Direct API endpoint to view tasks."""
    return {
        "tasks": get_tasks(status=status)
    }


@app.post("/tasks")
def create_task_endpoint(req: TaskCreateRequest):
    """Direct API endpoint to create a task."""
    task = create_task(title=req.title, priority=req.priority, due_date=req.due_date)
    return {
        "success": True,
        "task": task
    }


@app.post("/tasks/{task_id}/complete")
def complete_task_endpoint(task_id: int):
    """Direct API endpoint to complete a task."""
    task = complete_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task #{task_id} not found.")
    return {
        "success": True,
        "task": task
    }