from .orchestrator import (
    AgentOrchestrator,
    default_orchestrator
)
from .intent_analyzer import IntentAnalyzer
from .planner import TaskPlanner
from .tool_selector import ToolSelector
from .executor import ToolExecutor
from .verifier import ActionVerifier
from .memory import AgentMemory
from .providers import get_ai_provider, LocalProvider, BedrockProvider
from .prompts import SYSTEM_ORCHESTRATOR_PROMPT, INTENT_DETECTION_PROMPT, PLANNING_PROMPT

# Legacy imports for backward-compatible test suites
try:
    from . import legacy_agent
except ImportError:
    from backend.agent import legacy_agent

MODEL_NAME = legacy_agent.MODEL_NAME
TOOLS = legacy_agent.TOOLS
execute_tool = legacy_agent.execute_tool
handle_local_intent = legacy_agent.handle_local_intent


def get_client():
    return legacy_agent.get_client()


_orig_get_client = get_client


def run_agent(user_message: str, confirmed_action=None):
    # Check if get_client was monkeypatched on this module by test fixtures
    import backend.agent as self_mod
    cur_client_fn = getattr(self_mod, "get_client", None)
    if cur_client_fn and cur_client_fn != _orig_get_client:
        legacy_agent.get_client = cur_client_fn
    return legacy_agent.run_agent(user_message, confirmed_action)


__all__ = [
    "AgentOrchestrator",
    "default_orchestrator",
    "IntentAnalyzer",
    "TaskPlanner",
    "ToolSelector",
    "ToolExecutor",
    "ActionVerifier",
    "AgentMemory",
    "get_ai_provider",
    "LocalProvider",
    "BedrockProvider",
    "SYSTEM_ORCHESTRATOR_PROMPT",
    "INTENT_DETECTION_PROMPT",
    "PLANNING_PROMPT",
    # Legacy exports
    "run_agent",
    "get_client",
    "execute_tool",
    "handle_local_intent",
    "MODEL_NAME",
    "TOOLS"
]
