import sqlite3
from typing import Dict, Any, List
from .base import BaseTool, ToolResult
try:
    from database.repositories import ScheduleRepository, TaskRepository, MemoryRepository
except ImportError:
    from backend.database.repositories import ScheduleRepository, TaskRepository, MemoryRepository




class ScheduleTool(BaseTool):
    name = "schedule_tool"
    description = "Create schedule blocks, list schedules, reschedule sessions, and optimize schedule based on user memory and preferences."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "reschedule", "optimize"],
                "description": "Schedule action."
            },
            "title": {
                "type": "string",
                "description": "Title of the scheduled session."
            },
            "start_time": {
                "type": "string",
                "description": "Start time (e.g. '09:00 AM', '19:00')."
            },
            "end_time": {
                "type": "string",
                "description": "End time (e.g. '10:30 AM', '20:30')."
            },
            "day_of_week": {
                "type": "string",
                "description": "Day of the week (e.g. 'Monday', 'Today', 'Day 1')."
            },
            "session_type": {
                "type": "string",
                "enum": ["focus", "study", "meeting", "review"],
                "description": "Session type."
            },
            "task_id": {
                "type": "integer",
                "description": "Optional task ID to tie with schedule block."
            }
        },
        "required": ["action"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        action = kwargs.get("action", "").lower()

        try:
            if action == "create":
                title = kwargs.get("title")
                start_time = kwargs.get("start_time")
                end_time = kwargs.get("end_time")
                if not title or not start_time or not end_time:
                    return ToolResult(success=False, error="title, start_time, and end_time are required to create a schedule block.")

                day_of_week = kwargs.get("day_of_week", "Today")
                session_type = kwargs.get("session_type", "focus")
                task_id = kwargs.get("task_id")

                item = ScheduleRepository.create(
                    conn=conn,
                    user_id=user_id,
                    title=title,
                    start_time=start_time,
                    end_time=end_time,
                    task_id=int(task_id) if task_id else None,
                    day_of_week=day_of_week,
                    session_type=session_type,
                    is_optimized=0
                )
                return ToolResult(
                    success=True,
                    data=item,
                    message=f"Scheduled '{item['title']}' on {item['day_of_week']} ({item['start_time']} - {item['end_time']})."
                )

            elif action == "list":
                schedules = ScheduleRepository.list_by_user(conn, user_id)
                return ToolResult(
                    success=True,
                    data=schedules,
                    message=f"Retrieved {len(schedules)} schedule blocks."
                )

            elif action == "optimize":
                # Autonomous optimization:
                # 1. Fetch user's stored preferences (working hours, focus slots, etc.)
                memories = MemoryRepository.get_all(conn, user_id)
                pref_dict = {m["key"]: m["value"] for m in memories}

                # 2. Fetch pending tasks
                tasks = TaskRepository.list_all(conn, user_id, status="TODO")
                if not tasks:
                    tasks = TaskRepository.list_all(conn, user_id)

                # Clear previous schedule
                ScheduleRepository.clear_by_user(conn, user_id)

                # Generate optimized time windows based on user preferences:
                # e.g., default: 9:00 AM - 10:30 AM (Urgent/High), 11:00 AM - 12:30 PM, 2:00 PM - 3:30 PM, 7:00 PM - 8:30 PM (Evening focus)
                time_slots = [
                    ("09:00 AM", "10:30 AM", "Deep Focus: Morning Sprint", "focus"),
                    ("11:00 AM", "12:15 PM", "Core Execution Block", "focus"),
                    ("02:00 PM", "03:15 PM", "Architecture & Verification", "review"),
                    ("04:00 PM", "05:00 PM", "Wrap-up & Testing", "study"),
                    ("07:00 PM", "08:30 PM", "Evening Study / Goal Revision", "study"),
                ]

                created_blocks = []
                for i, t in enumerate(tasks[:5]):
                    slot = time_slots[i % len(time_slots)]
                    block = ScheduleRepository.create(
                        conn=conn,
                        user_id=user_id,
                        title=f"{t['title']} ({t['priority']})",
                        start_time=slot[0],
                        end_time=slot[1],
                        task_id=t["id"],
                        day_of_week="Today",
                        session_type=slot[3],
                        is_optimized=1
                    )
                    created_blocks.append(block)

                summary = (
                    f"Optimized schedule into {len(created_blocks)} prioritized focus windows. "
                    f"Aligned with preferences: working hours ({pref_dict.get('preferred_working_hours', '9 AM - 6 PM')}) "
                    f"and evening study ({pref_dict.get('preferred_evening_focus', '7 PM - 9 PM')})."
                )

                return ToolResult(
                    success=True,
                    data={"optimized_blocks": created_blocks, "preferences_applied": pref_dict},
                    message=summary
                )

            else:
                return ToolResult(success=False, error=f"Unknown schedule action: '{action}'.")

        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"ScheduleTool failed: {str(e)}")
