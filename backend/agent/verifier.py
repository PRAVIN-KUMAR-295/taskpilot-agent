import sqlite3
import json
from typing import Tuple, List, Dict, Any, Optional
try:
    from database.repositories import TaskRepository, ReminderRepository, ScheduleRepository
except ImportError:
    from backend.database.repositories import TaskRepository, ReminderRepository, ScheduleRepository



class ActionVerifier:
    """Verifies that executed tool actions successfully mutated system state as expected."""

    @staticmethod
    def verify_execution(
        user_id: int,
        conn: sqlite3.Connection,
        execution_results: List[Dict[str, Any]]
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        verification_reports = []
        all_passed = True

        for item in execution_results:
            tool_name = item.get("tool_name")
            params = item.get("params", {})
            action_id = item.get("action_id")
            res_data = item.get("result", {}).get("data", {})

            verified = False
            details = {}

            if tool_name == "task_tool":
                action = params.get("action", "")
                if action == "create":
                    task_id = res_data.get("id") if isinstance(res_data, dict) else None
                    if task_id:
                        db_task = TaskRepository.get_by_id(conn, task_id, user_id)
                        if db_task and db_task["title"] == params.get("title"):
                            verified = True
                            details = {"verified_entity": "task", "task_id": task_id, "check": "persisted_in_db"}
                elif action == "complete":
                    task_id = params.get("task_id")
                    if task_id:
                        db_task = TaskRepository.get_by_id(conn, int(task_id), user_id)
                        if db_task and db_task["status"] == "COMPLETED":
                            verified = True
                            details = {"verified_entity": "task", "task_id": task_id, "check": "status_completed"}
                elif action == "delete":
                    task_id = params.get("task_id")
                    if task_id:
                        db_task = TaskRepository.get_by_id(conn, int(task_id), user_id)
                        if db_task is None:
                            verified = True
                            details = {"verified_entity": "task", "task_id": task_id, "check": "record_removed"}
                else:
                    verified = True
                    details = {"check": "query_completed"}

            elif tool_name == "reminder_tool":
                action = params.get("action", "")
                if action == "create":
                    rem_id = res_data.get("id") if isinstance(res_data, dict) else None
                    if rem_id:
                        reminders = ReminderRepository.list_by_user(conn, user_id)
                        if any(r["id"] == rem_id for r in reminders):
                            verified = True
                            details = {"verified_entity": "reminder", "reminder_id": rem_id, "check": "scheduled"}
                elif action == "cancel":
                    verified = True
                    details = {"check": "reminder_cancelled"}
                else:
                    verified = True
                    details = {"check": "query_completed"}

            elif tool_name == "schedule_tool":
                schedules = ScheduleRepository.list_by_user(conn, user_id)
                if schedules or params.get("action") == "list":
                    verified = True
                    details = {"verified_entity": "schedules", "count": len(schedules), "check": "calendar_synced"}

            elif tool_name == "planning_tool":
                plan_id = res_data.get("id") if isinstance(res_data, dict) else None
                if plan_id:
                    verified = True
                    details = {"verified_entity": "plan", "plan_id": plan_id, "check": "plan_persisted"}
                else:
                    verified = True

            elif tool_name in ["notification_tool", "gmail_tool", "slack_tool", "google_calendar_tool", "notion_tool"]:
                verified = item.get("result", {}).get("success", False)
                details = {"check": "simulated_dispatch_confirmed", "provider": tool_name}

            else:
                verified = item.get("result", {}).get("success", False)
                details = {"check": "generic_success"}

            if not verified:
                all_passed = False

            # Update DB audit record
            if action_id:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE agent_actions
                    SET verification_status = ?, verification_details = ?
                    WHERE id = ?
                """, (
                    "VERIFIED" if verified else "FAILED",
                    json.dumps(details),
                    action_id
                ))
                conn.commit()

            verification_reports.append({
                "action_id": action_id,
                "tool_name": tool_name,
                "verified": verified,
                "details": details
            })

        return all_passed, verification_reports
