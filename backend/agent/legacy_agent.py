import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

from config import OPENAI_API_KEY, MODEL_NAME, is_openai_configured
from tools import (
    tool_get_tasks,
    tool_create_task,
    tool_complete_task,
    tool_delete_task,
    tool_clear_all_tasks,
    tool_search,
    is_risky_action,
    RISKY_ACTIONS
)
from services.memory_service import (
    get_recent_memory,
    save_memory,
)

# Initialize OpenAI client safely
_client = None


def get_client() -> Optional[Any]:
    """Get or initialize OpenAI client."""
    global _client
    if _client is None and is_openai_configured() and OpenAI is not None:
        try:
            _client = OpenAI(api_key=OPENAI_API_KEY, timeout=3.0, max_retries=0)
        except Exception:
            _client = None
    return _client



# ==========================================
# Agent Tools Specification
# ==========================================

TOOLS = [
    {
        "type": "function",
        "name": "get_tasks",
        "description": "Get tasks of the user, optionally filtered by status ('pending' or 'completed').",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "completed"],
                    "description": "Filter by status: 'pending' or 'completed'.",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "create_task",
        "description": "Create a new task with title, priority, and optional due date or time.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The task title.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Task priority level.",
                },
                "due_date": {
                    "type": "string",
                    "description": "Optional due date or time (e.g., 'tomorrow', '2026-09-27', '5:00 PM').",
                },
            },
            "required": ["title"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "complete_task",
        "description": "Mark an existing task as completed by its integer ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to complete.",
                },
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "delete_task",
        "description": "Permanently delete a task by its ID (destructive/risky action requiring confirmation).",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to delete.",
                },
            },
            "required": ["task_id"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "clear_all_tasks",
        "description": "Permanently clear all tasks in the system (destructive/risky action requiring confirmation).",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_information",
        "description": "Search real-world information and facts for the user using live knowledge.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query keywords.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]

# ==========================================
# System Instructions
# ==========================================

SYSTEM_INSTRUCTIONS = """You are TaskPilot, an autonomous AI productivity agent for everyday tasks.
Your job is to understand user requests, plan actions, use tools accurately, and return clear results.

Available tools:
- get_tasks: Retrieve user tasks (optionally by status: 'pending' or 'completed').
- create_task: Create a task with title, priority (low, medium, high), and optional due_date.
- complete_task: Mark a task complete using its integer ID.
- delete_task: Permanently delete a task by ID (risky action).
- clear_all_tasks: Permanently delete all tasks (risky action).
- search_information: Search real external information for facts or queries.

Guidelines:
1. Always use the appropriate tool for task creation, listing, completion, and information search.
2. If the user asks to create a task, extract the title, priority if mentioned, and due date/time if mentioned (e.g. 'tomorrow', 'Friday 5pm').
3. Never claim that a task was created or completed unless the tool execution succeeded.
4. For risky actions (delete_task, clear_all_tasks), warn the user if confirmation is needed.
5. Be concise, organized, and helpful.
"""


# ==========================================
# Execute Tool
# ==========================================

def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered tool by name with arguments."""
    try:
        if name == "get_tasks":
            return tool_get_tasks(status=arguments.get("status"))

        if name == "create_task":
            return tool_create_task(
                title=arguments.get("title", ""),
                priority=arguments.get("priority", "medium"),
                due_date=arguments.get("due_date")
            )

        if name == "complete_task":
            return tool_complete_task(arguments.get("task_id"))

        if name == "delete_task":
            return tool_delete_task(arguments.get("task_id"))

        if name == "clear_all_tasks":
            return tool_clear_all_tasks()

        if name == "search_information":
            return tool_search(arguments.get("query", ""))

        return {
            "success": False,
            "error": f"Unknown tool: '{name}'"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Tool execution failed for '{name}': {str(e)}"
        }


# ==========================================
# Build Memory
# ==========================================

def build_memory() -> str:
    """Format recent memory context into instructions."""
    memory = get_recent_memory(limit=5)
    if not memory:
        return ""

    text = "\n\nRecent conversation context:\n"
    for item in memory:
        text += f"User: {item.get('user', '')}\nAssistant: {item.get('assistant', '')}\n"
    return text


# ==========================================
# Local Intent Parser (Offline / Zero Credit Fallback)
# ==========================================

def handle_local_intent(
    user_message: str,
    confirmed_action: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Deterministically handles common task & search commands locally.
    Enables local testing without consuming API credits, and provides
    clear, non-faked handling when OpenAI quota is exhausted.
    """
    msg = user_message.strip()
    msg_lower = msg.lower()

    # 1. Handle pre-confirmed action execution
    if confirmed_action:
        tool_name = confirmed_action.get("tool_name")
        args = confirmed_action.get("arguments", {})
        result = execute_tool(tool_name, args)
        if result.get("success"):
            answer = f"Action confirmed: {result.get('message', 'Completed successfully.')}"
            save_memory(user_message, answer)
            return {
                "response": answer,
                "success": True,
                "tasks": None,
                "action_pending_approval": None
            }
        else:
            answer = f"Action failed: {result.get('error') or result.get('message')}"
            return {
                "response": answer,
                "success": False,
                "tasks": None,
                "action_pending_approval": None
            }

    # 2. Check for task listing
    if any(phrase in msg_lower for phrase in ["list task", "show task", "pending task", "my task", "get task", "view task"]):
        status = "pending" if "pending" in msg_lower else ("completed" if "completed" in msg_lower else None)
        result = tool_get_tasks(status=status)
        tasks = result.get("tasks", [])
        if not tasks:
            filter_text = f" ({status})" if status else ""
            ans = f"You currently have no{filter_text} tasks."
        else:
            ans = f"Here are your {status or 'stored'} tasks ({len(tasks)} found):\n"
            for t in tasks:
                due_info = f" | Due: {t['due_date']}" if t.get("due_date") else ""
                ans += f"- [#{t['id']}] {t['title']} (Priority: {t.get('priority', 'medium')}, Status: {t.get('status', 'pending')}{due_info})\n"
        save_memory(user_message, ans)
        return {
            "response": ans.strip(),
            "success": True,
            "tasks": tasks,
            "action_pending_approval": None
        }

    # 3. Check for task creation
    create_match = re.search(r"(?:create|add|new)\s+(?:a\s+)?task\s+(?:to\s+)?(.+)", msg, re.IGNORECASE)
    if create_match:
        raw_content = create_match.group(1).strip()
        # Parse optional priority
        priority = "medium"
        for p in ["high", "medium", "low"]:
            if f"priority {p}" in raw_content.lower() or f"{p} priority" in raw_content.lower():
                priority = p
                raw_content = re.sub(rf"(?:with\s+)?(?:priority\s+{p}|{p}\s+priority)", "", raw_content, flags=re.IGNORECASE).strip()

        # Parse optional due date
        due_date = None
        due_match = re.search(r"(?:due|by|tomorrow|tonight|next week|at \d{1,2}(?::\d{2})?\s*(?:am|pm)?).*$", raw_content, re.IGNORECASE)
        if due_match:
            due_date = due_match.group(0).strip()
            # clean title
            title = raw_content[:due_match.start()].strip()
            if not title:
                title = raw_content
        else:
            title = raw_content

        if title:
            result = tool_create_task(title=title, priority=priority, due_date=due_date)
            created_task = result.get("task")
            due_str = f" with due date '{due_date}'" if due_date else ""
            ans = f"Task #{created_task['id']} ('{created_task['title']}') has been created with {priority} priority{due_str}."
            save_memory(user_message, ans)
            return {
                "response": ans,
                "success": True,
                "tasks": [created_task],
                "action_pending_approval": None
            }

    # 4. Check for task completion
    complete_match = re.search(r"(?:complete|finish|done|mark\s+done)\s+(?:task\s+)?#?(\d+)", msg, re.IGNORECASE)
    if complete_match:
        task_id = int(complete_match.group(1))
        result = tool_complete_task(task_id)
        if result.get("success"):
            ans = f"Task #{task_id} ('{result['task']['title']}') has been marked as completed."
            save_memory(user_message, ans)
            return {
                "response": ans,
                "success": True,
                "tasks": [result["task"]],
                "action_pending_approval": None
            }
        else:
            ans = result.get("message", f"Task #{task_id} not found.")
            return {
                "response": ans,
                "success": False,
                "tasks": None,
                "action_pending_approval": None
            }

    # 5. Check for task deletion (Risky action -> trigger approval!)
    delete_match = re.search(r"(?:delete|remove)\s+(?:task\s+)?#?(\d+)", msg, re.IGNORECASE)
    if delete_match:
        task_id = int(delete_match.group(1))
        approval = {
            "action_type": "delete_task",
            "tool_name": "delete_task",
            "arguments": {"task_id": task_id},
            "prompt": f"Are you sure you want to permanently delete Task #{task_id}?",
            "warning": "This action cannot be undone."
        }
        ans = f"[CONFIRMATION REQUIRED] Confirmation Required: Deleting Task #{task_id} is a permanent action. Please confirm or cancel below."
        return {
            "response": ans,
            "success": True,
            "tasks": None,
            "action_pending_approval": approval
        }

    # 6. Check for clear all tasks (Risky action -> trigger approval!)
    if any(phrase in msg_lower for phrase in ["clear all tasks", "delete all tasks", "remove all tasks"]):
        approval = {
            "action_type": "clear_all_tasks",
            "tool_name": "clear_all_tasks",
            "arguments": {},
            "prompt": "Are you sure you want to permanently delete ALL tasks in the system?",
            "warning": "All stored tasks will be erased permanently."
        }
        ans = "[CONFIRMATION REQUIRED] Confirmation Required: Clearing all tasks is a destructive action. Please confirm or cancel below."
        return {
            "response": ans,
            "success": True,
            "tasks": None,
            "action_pending_approval": approval
        }

    # 7. Check for search
    search_match = re.search(r"(?:search|find info on|lookup|who is|what is)(?:\s+for|\s+about)?\s+(.+)", msg, re.IGNORECASE)
    if search_match:
        query = search_match.group(1).strip()
        result = tool_search(query)
        if result.get("success"):
            ans = f"Search Results for '{result['query']}':\n{result.get('summary', 'No summary available.')}\n\nSources:\n"
            for r in result.get("results", []):
                ans += f"- {r['title']}: {r['url']}\n"
        else:
            ans = f"Search failed: {result.get('error', 'Unable to retrieve results.')}"
        save_memory(user_message, ans)
        return {
            "response": ans.strip(),
            "success": result.get("success", False),
            "tasks": None,
            "action_pending_approval": None
        }

    return None


# ==========================================
# Run Agent
# ==========================================

def run_agent(
    user_message: str,
    confirmed_action: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main entry point for agent execution.
    Supports:
    - Pre-confirmed human approvals
    - Intercepting risky actions before execution
    - Multi-step tool execution with OpenAI
    - Comprehensive OpenAI error handling (401, 429 quota exhausted, connection errors)
    - Honest offline task/search handling when OpenAI quota is exhausted
    """
    clean_message = user_message.strip()
    if not clean_message:
        return {
            "response": "Please enter a message or command.",
            "success": False,
            "tasks": None,
            "action_pending_approval": None
        }

    # Step 1: If user supplied a confirmed risky action, execute immediately
    if confirmed_action:
        tool_name = confirmed_action.get("tool_name")
        args = confirmed_action.get("arguments", {})
        result = execute_tool(tool_name, args)
        if result.get("success"):
            ans = f"Confirmed action executed: {result.get('message', 'Success.')}"
            save_memory(clean_message, ans)
            return {
                "response": ans,
                "success": True,
                "tasks": None,
                "action_pending_approval": None
            }
        else:
            ans = f"Execution failed: {result.get('error') or result.get('message')}"
            return {
                "response": ans,
                "success": False,
                "tasks": None,
                "action_pending_approval": None
            }

    # Step 2: Try OpenAI Agent Execution if client is configured
    client = get_client()

    if client is not None:
        try:
            memory = build_memory()
            instructions = SYSTEM_INSTRUCTIONS + memory

            # Call OpenAI Responses API
            response = client.responses.create(
                model=MODEL_NAME,
                instructions=instructions,
                input=clean_message,
                tools=TOOLS,
            )

            tool_outputs = []
            extracted_tasks = []
            pending_approval = None

            # Process tool calls
            for item in response.output:
                if getattr(item, "type", None) == "function_call":
                    func_name = item.name
                    func_args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments

                    # Check for risky action requiring confirmation
                    if is_risky_action(func_name):
                        risk_info = RISKY_ACTIONS[func_name]
                        pending_approval = {
                            "action_type": func_name,
                            "tool_name": func_name,
                            "arguments": func_args,
                            "prompt": f"Are you sure you want to execute '{func_name}' with parameters {func_args}?",
                            "warning": risk_info.get("warning", "This action requires human approval.")
                        }
                        ans = (
                            f"[CONFIRMATION REQUIRED] Confirmation Required: You requested '{func_name}', which is a high-risk action.\n"
                            f"Warning: {risk_info.get('warning')}\n"
                            f"Please confirm or cancel this action below."
                        )
                        return {
                            "response": ans,
                            "success": True,
                            "action_pending_approval": pending_approval,
                            "tasks": None
                        }

                    # Execute safe tool
                    tool_res = execute_tool(func_name, func_args)

                    if func_name in ("get_tasks", "create_task", "complete_task"):
                        if "tasks" in tool_res:
                            extracted_tasks.extend(tool_res["tasks"])
                        elif "task" in tool_res:
                            extracted_tasks.append(tool_res["task"])

                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(tool_res),
                    })

            # If tools were invoked, request final synthesis from agent
            if tool_outputs:
                final_response = client.responses.create(
                    model=MODEL_NAME,
                    instructions=instructions,
                    input=[
                        {"role": "user", "content": clean_message},
                        *response.output,
                        *tool_outputs,
                    ],
                    tools=TOOLS,
                )
                answer = getattr(final_response, "output_text", "")
            else:
                answer = getattr(response, "output_text", "")

            save_memory(clean_message, answer)
            return {
                "response": answer,
                "success": True,
                "tasks": extracted_tasks if extracted_tasks else None,
                "action_pending_approval": None
            }

        except openai.AuthenticationError:
            err_msg = (
                "OpenAI Authentication Error (401): The configured OPENAI_API_KEY is invalid. "
                "Please verify your key in the .env file."
            )
            # Check if user message can be handled locally
            local_res = handle_local_intent(clean_message)
            if local_res:
                local_res["response"] = f"[Notice: OpenAI 401 Auth Error - handled via local task engine]\n\n" + local_res["response"]
                return local_res
            return {
                "response": err_msg,
                "success": False,
                "error": "AuthenticationError"
            }

        except openai.RateLimitError as e:
            # Explicitly handled as requested: user's OpenAI quota is currently exhausted
            local_res = handle_local_intent(clean_message)
            if local_res:
                local_res["response"] = (
                    f"[Notice: OpenAI Quota Exhausted (429) - executed via local task engine]\n\n"
                    + local_res["response"]
                )
                return local_res

            quota_msg = (
                "OpenAI API Quota Exhausted (429: credit_balance_exhausted):\n"
                "Your OpenAI account has no remaining API credits. To use generative chat reasoning, "
                "add credits at https://platform.openai.com/account/billing.\n\n"
                "Tip: You can still use TaskPilot commands locally, such as:\n"
                "- 'Create a task to prepare hackathon presentation tomorrow'\n"
                "- 'Show me my pending tasks'\n"
                "- 'Complete task #1'\n"
                "- 'Delete task #1' (triggers Human Approval)\n"
                "- 'Search for Artificial Intelligence'"
            )
            return {
                "response": quota_msg,
                "success": True,  # Graceful response per instructions
                "error": "RateLimitError"
            }

        except (openai.APIConnectionError, TimeoutError):
            local_res = handle_local_intent(clean_message)
            if local_res:
                local_res["response"] = "[Notice: Network connection to OpenAI timed out - handled via local task engine]\n\n" + local_res["response"]
                return local_res
            return {
                "response": "Network error: Unable to reach OpenAI servers. Please check your internet connection.",
                "success": False,
                "error": "APIConnectionError"
            }

        except Exception as e:
            local_res = handle_local_intent(clean_message)
            if local_res:
                local_res["response"] = f"[Notice: Handled via local task engine]\n\n" + local_res["response"]
                return local_res
            return {
                "response": f"Agent error: {str(e)}",
                "success": False,
                "error": str(e)
            }

    # Step 3: If OpenAI is not configured or key is empty
    local_res = handle_local_intent(clean_message)
    if local_res:
        return local_res

    return {
        "response": (
            "TaskPilot is running in local mode (OpenAI API key not configured or unavailable).\n\n"
            "Supported local commands:\n"
            "- 'Create task <title> [priority high/medium/low] [due <date>]'\n"
            "- 'Show pending tasks'\n"
            "- 'Complete task <id>'\n"
            "- 'Delete task <id>'\n"
            "- 'Search <query>'"
        ),
        "success": True,
        "tasks": None,
        "action_pending_approval": None
    }