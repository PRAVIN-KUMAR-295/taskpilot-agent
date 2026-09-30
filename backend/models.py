from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


# Auth Schemas
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=150)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    token: str
    user: Dict[str, Any]
    message: str = ""


# Task Schemas
class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    priority: Optional[str] = "MEDIUM"  # LOW, MEDIUM, HIGH, URGENT
    status: Optional[str] = "TODO"      # TODO, IN_PROGRESS, COMPLETED, BLOCKED
    due_date: Optional[str] = None
    estimated_duration: Optional[int] = 30
    category: Optional[str] = "General"
    dependencies: Optional[List[int]] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    estimated_duration: Optional[int] = None
    category: Optional[str] = None
    dependencies: Optional[List[int]] = None


class TaskItem(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = ""
    priority: str
    status: str
    due_date: Optional[str] = None
    estimated_duration: int
    category: str
    source: str
    created_at: str
    updated_at: str


# Reminder Schemas
class ReminderCreateRequest(BaseModel):
    title: str
    reminder_time: str
    task_id: Optional[int] = None
    channel: Optional[str] = "in_app"


# Schedule Schemas
class ScheduleCreateRequest(BaseModel):
    title: str
    start_time: str
    end_time: str
    task_id: Optional[int] = None
    day_of_week: Optional[str] = "Today"
    session_type: Optional[str] = "focus"


# Memory Schemas
class MemoryCreateRequest(BaseModel):
    key: str
    value: str
    category: Optional[str] = "preference"


# Agent Schemas
class AgentRunRequest(BaseModel):
    goal: Optional[str] = ""
    message: Optional[str] = ""  # alias for goal
    run_id: Optional[str] = None
    confirmed_action: Optional[Dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    confirmed_action: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    success: bool = True
    action_pending_approval: Optional[Dict[str, Any]] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None