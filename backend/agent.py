import json

from openai import OpenAI

from config import OPENAI_API_KEY, MODEL_NAME

from tools import (
    tool_get_tasks,
    tool_create_task,
    tool_complete_task,
    tool_search,
)

from services.memory_service import (
    get_recent_memory,
    save_memory,
)


# ==========================================
# OpenAI Client
# ==========================================

client = OpenAI(
    api_key=OPENAI_API_KEY
)


# ==========================================
# Agent Tools
# ==========================================

TOOLS = [
    {
        "type": "function",
        "name": "get_tasks",
        "description": "Get all tasks of the user.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "create_task",
        "description": "Create a new task.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The task title.",
                },
                "priority": {
                    "type": "string",
                    "enum": [
                        "low",
                        "medium",
                        "high",
                    ],
                },
            },
            "required": [
                "title",
                "priority",
            ],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "complete_task",
        "description": "Complete an existing task.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID of the task to complete.",
                },
            },
            "required": [
                "task_id",
            ],
            "additionalProperties": False,
        },
    },

    {
        "type": "function",
        "name": "search_information",
        "description": "Search information for the user.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query.",
                },
            },
            "required": [
                "query",
            ],
            "additionalProperties": False,
        },
    },
]


# ==========================================
# System Instructions
# ==========================================

SYSTEM_INSTRUCTIONS = """
You are TaskPilot, an autonomous AI productivity agent.

Understand the user's request and decide what action is needed.

Available tools:

- get_tasks
- create_task
- complete_task
- search_information

Use tools when necessary.

Never claim that a task was created unless
the create_task tool succeeds.

Never claim that a task was completed unless
the complete_task tool succeeds.

If multiple actions are required, perform them
in a logical order.

Be concise, helpful, and accurate.
"""


# ==========================================
# Execute Tool
# ==========================================

def execute_tool(name, arguments):

    if name == "get_tasks":
        return tool_get_tasks()

    if name == "create_task":
        return tool_create_task(
            arguments["title"],
            arguments["priority"],
        )

    if name == "complete_task":
        return tool_complete_task(
            arguments["task_id"],
        )

    if name == "search_information":
        return tool_search(
            arguments["query"],
        )

    return {
        "success": False,
        "error": f"Unknown tool: {name}",
    }


# ==========================================
# Build Memory
# ==========================================

def build_memory():

    memory = get_recent_memory()

    if not memory:
        return ""

    text = "\nRecent conversation:\n"

    for item in memory:

        text += (
            f"User: {item['user']}\n"
            f"Assistant: {item['assistant']}\n"
        )

    return text


# ==========================================
# Run Agent
# ==========================================

def run_agent(user_message):

    memory = build_memory()

    response = client.responses.create(
        model=MODEL_NAME,

        instructions=(
            SYSTEM_INSTRUCTIONS
            + memory
        ),

        input=user_message,

        tools=TOOLS,
    )

    tool_outputs = []

    for item in response.output:

        if item.type == "function_call":

            arguments = json.loads(
                item.arguments
            )

            result = execute_tool(
                item.name,
                arguments,
            )

            tool_outputs.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": json.dumps(result),
                }
            )

    # ==========================================
    # If tools were used, get final response
    # ==========================================

    if tool_outputs:

        final_response = client.responses.create(
            model=MODEL_NAME,

            instructions=(
                SYSTEM_INSTRUCTIONS
                + memory
            ),

            input=[
                {
                    "role": "user",
                    "content": user_message,
                },

                *response.output,

                *tool_outputs,
            ],

            tools=TOOLS,
        )

        answer = final_response.output_text

    else:

        answer = response.output_text

    # ==========================================
    # Save conversation memory
    # ==========================================

    save_memory(
        user_message,
        answer,
    )

    return answer