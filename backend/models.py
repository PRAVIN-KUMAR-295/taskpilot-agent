from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User request message")
    confirmed_action: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Action payload confirmed by user for risky operations"
    )


class TaskItem(BaseModel):
    id: int
    title: str
    priority: str = Field(default="medium")
    status: str = Field(default="pending")  # "pending" or "completed"
    completed: bool = Field(default=False)
    due_date: Optional[str] = Field(default=None)
    created_at: str


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    priority: str = Field(default="medium")
    due_date: Optional[str] = Field(default=None)


class TaskCompleteRequest(BaseModel):
    task_id: int


class ActionApproval(BaseModel):
    action_type: str
    tool_name: str
    arguments: Dict[str, Any]
    prompt: str
    warning: str


class ChatResponse(BaseModel):
    response: str
    success: bool = True
    action_pending_approval: Optional[ActionApproval] = None
    tasks: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None