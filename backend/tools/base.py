from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, NamedTuple
import sqlite3


class ToolResult:
    """Structured result returned by every tool execution."""
    def __init__(
        self,
        success: bool,
        data: Any = None,
        message: str = "",
        error: Optional[str] = None,
        requires_confirmation: bool = False,
        confirmation_prompt: Optional[str] = None
    ):
        self.success = success
        self.data = data
        self.message = message
        self.error = error
        self.requires_confirmation = requires_confirmation
        self.confirmation_prompt = confirmation_prompt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error": self.error,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_prompt": self.confirmation_prompt
        }


class BaseTool(ABC):
    """Abstract base class for all TaskPilot agent tools."""

    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}
    is_simulated: bool = False
    requires_confirmation_by_default: bool = False

    def validate_input(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validates tool parameters against required keys in input_schema."""
        required = self.input_schema.get("required", [])
        for field in required:
            if field not in params or params[field] is None:
                return False, f"Missing required parameter '{field}' for tool '{self.name}'."
        return True, None

    def check_requires_confirmation(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Determines if this specific invocation requires user approval."""
        if self.requires_confirmation_by_default:
            return True, f"Action with tool '{self.name}' requires user confirmation."
        return False, None

    @abstractmethod
    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        """Executes the tool logic with user context and database connection."""
        pass

    def to_spec(self) -> Dict[str, Any]:
        """Returns OpenAI/Bedrock compatible tool specification."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": f"{self.description} [Demo / Simulated Tool]" if self.is_simulated else self.description,
                "parameters": self.input_schema
            },
            "is_simulated": self.is_simulated,
            "requires_confirmation": self.requires_confirmation_by_default
        }
