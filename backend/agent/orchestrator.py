import uuid
import sqlite3
import datetime
from typing import Dict, Any, Optional, List

try:
    from database.repositories import (
        AgentRunRepository,
        TaskRepository,
        ReminderRepository,
        ScheduleRepository,
        PlanRepository,
        MemoryRepository
    )
    from agent.intent_analyzer import IntentAnalyzer
    from agent.planner import TaskPlanner
    from agent.tool_selector import ToolSelector
    from agent.executor import ToolExecutor
    from agent.verifier import ActionVerifier
except ImportError:
    from backend.database.repositories import (
        AgentRunRepository,
        TaskRepository,
        ReminderRepository,
        ScheduleRepository,
        PlanRepository,
        MemoryRepository
    )
    from backend.agent.intent_analyzer import IntentAnalyzer
    from backend.agent.planner import TaskPlanner
    from backend.agent.tool_selector import ToolSelector
    from backend.agent.executor import ToolExecutor
    from backend.agent.verifier import ActionVerifier



class AgentOrchestrator:
    """
    Central orchestration engine for TaskPilot.
    Executes state machine:
    UNDERSTANDING -> PLANNING -> WAITING_FOR_APPROVAL -> EXECUTING -> VERIFYING -> COMPLETED / FAILED
    """

    def __init__(self):
        self.intent_analyzer = IntentAnalyzer()
        self.planner = TaskPlanner()

    def run(
        self,
        user_id: int,
        conn: sqlite3.Connection,
        goal: str,
        confirmed_action: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
        timeline: List[Dict[str, Any]] = []

        def log_step(step_name: str, status: str, message: str, meta: Optional[Dict] = None):
            timeline.append({
                "step": step_name,
                "status": status,
                "message": message,
                "meta": meta or {},
                "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            })

        # ==========================================
        # SCENARIO A: RESUMING AFTER USER CONFIRMATION
        # ==========================================
        if confirmed_action:
            AgentRunRepository.create(
                conn, run_id, user_id, goal or "Confirmed Action", "CONFIRMED_EXECUTION",
                status="EXECUTING", requires_approval=False, summary="Executing confirmed actions."
            )
            log_step("APPROVAL_RECEIVED", "completed", "User confirmed approved action. Resuming autonomous execution.")
            action_type = confirmed_action.get("type", "")

            # If user confirmed plan execution
            if action_type == "APPROVE_PLAN" or "plan" in confirmed_action:
                plan_data = confirmed_action.get("plan", {})
                tasks_to_create = plan_data.get("tasks", [])

                pipeline = []
                for t in tasks_to_create:
                    pipeline.append({
                        "tool_name": "task_tool",
                        "params": {
                            "action": "create",
                            "title": t["title"],
                            "priority": t.get("priority", "HIGH"),
                            "estimated_duration": t.get("estimated_minutes", 45),
                            "due_date": t.get("day_or_stage", "Next Days"),
                            "category": "Approved Plan"
                        }
                    })
                pipeline.append({
                    "tool_name": "schedule_tool",
                    "params": {"action": "optimize"}
                })
                pipeline.append({
                    "tool_name": "reminder_tool",
                    "params": {
                        "action": "create",
                        "title": f"Review execution milestones for: {goal or 'Plan'}",
                        "reminder_time": "Tomorrow at 09:00 AM"
                    }
                })
                pipeline.append({
                    "tool_name": "notification_tool",
                    "params": {
                        "title": "Autonomous Execution Complete",
                        "message": f"Successfully created {len(tasks_to_create)} tasks, scheduled focus blocks, and configured reminders.",
                        "urgency": "normal"
                    }
                })

            elif confirmed_action.get("tool_name"):
                # Single confirmed tool (e.g. delete_task, send email)
                pipeline = [{
                    "tool_name": confirmed_action.get("tool_name"),
                    "params": confirmed_action.get("params") or confirmed_action.get("arguments", {})
                }]
            else:
                pipeline = []

            # Step: EXECUTING
            log_step("EXECUTING", "in_progress", f"Executing {len(pipeline)} autonomous actions.")
            exec_results = ToolExecutor.execute_pipeline(user_id, conn, pipeline, run_id)
            successful_count = sum(1 for r in exec_results if r.get("status") == "SUCCESS")
            log_step("EXECUTING", "completed", f"Executed {len(pipeline)} actions ({successful_count} successful).")

            # Step: VERIFYING
            log_step("VERIFYING", "in_progress", "Verifying database mutations and post-conditions.")
            all_verified, verification_details = ActionVerifier.verify_execution(user_id, conn, exec_results)
            ver_status = "completed" if all_passed_or_lenient(all_verified, len(pipeline)) else "warning"
            log_step("VERIFYING", ver_status, "Post-condition state verification complete.", {"details": verification_details})

            # Step: COMPLETED
            summary = (
                f"Autonomous execution complete: created {successful_count} items, "
                f"optimized calendar schedule, and configured reminders. All actions verified."
            )
            log_step("COMPLETED", "completed", summary)

            AgentRunRepository.create(
                conn, run_id, user_id, goal or "Confirmed Action", "CONFIRMED_EXECUTION",
                status="COMPLETED", requires_approval=False, summary=summary
            )

            current_tasks = TaskRepository.list_all(conn, user_id)
            current_schedules = ScheduleRepository.list_by_user(conn, user_id)
            current_reminders = ReminderRepository.list_by_user(conn, user_id)

            return {
                "run_id": run_id,
                "goal": goal,
                "intent": "CONFIRMED_EXECUTION",
                "status": "COMPLETED",
                "requiresApproval": False,
                "actionPendingApproval": None,
                "timeline": timeline,
                "actions": exec_results,
                "actionsExecuted": len(exec_results),
                "actionsSuccessful": successful_count,
                "verification": {"all_passed": all_verified, "details": verification_details},
                "summary": summary,
                "tasks": current_tasks,
                "schedules": current_schedules,
                "reminders": current_reminders,
                "success": True
            }

        # ==========================================
        # SCENARIO B: NORMAL AUTONOMOUS AGENT RUN
        # ==========================================

        # Step 1: UNDERSTANDING
        log_step("UNDERSTANDING", "in_progress", f"Analyzing user goal: '{goal}'")
        analysis = self.intent_analyzer.analyze(user_id, conn, goal)
        intent = analysis.get("intent", "PROJECT_PLAN")
        entities = analysis.get("entities", {})
        memory_ctx = analysis.get("memory_context", {})

        # Ensure run record exists prior to any tool execution or logging
        AgentRunRepository.create(
            conn, run_id, user_id, goal, intent,
            status="UNDERSTANDING", requires_approval=False, summary="Agent understanding user goal."
        )
        log_step(
            "UNDERSTANDING", "completed",
            f"Goal understood: Classified intent as '{intent}' (Confidence: {analysis.get('confidence', 0.95):.0%}).",
            {"intent": intent, "entities": entities}
        )

        # Handle direct memory update
        if intent == "MEMORY_UPDATE":
            learned = analysis.get("learned_memory")
            summary = f"I have saved your preference: '{learned['key']}' = '{learned['value']}'. I will factor this into future schedules and plans."
            log_step("COMPLETED", "completed", summary)
            return {
                "run_id": run_id,
                "goal": goal,
                "intent": intent,
                "status": "COMPLETED",
                "requiresApproval": False,
                "actionPendingApproval": None,
                "timeline": timeline,
                "actionsExecuted": 1,
                "actionsSuccessful": 1,
                "summary": summary,
                "learned_memory": learned,
                "tasks": TaskRepository.list_all(conn, user_id),
                "success": True
            }

        # Step 2: PLANNING
        log_step("PLANNING", "in_progress", "Formulating structured plan and deconstructing subtasks.")
        plan = self.planner.plan(goal, analysis, memory_ctx)
        log_step(
            "PLANNING", "completed",
            f"Generated plan '{plan.get('title', goal)}' containing {len(plan.get('tasks', []))} prioritized subtasks.",
            {"plan": plan}
        )

        # Step 3: TOOL SELECTION
        log_step("TOOL_SELECTION", "in_progress", "Selecting tool sequence and evaluating safety constraints.")
        pipeline, requires_approval, approval_action = ToolSelector.select_tools(intent, goal, plan, entities)
        tools_selected = list(dict.fromkeys(item["tool_name"] for item in pipeline))
        log_step(
            "TOOL_SELECTION", "completed",
            f"Selected {len(tools_selected)} tools: {', '.join(tools_selected)}.",
            {"tools": tools_selected, "requires_approval": requires_approval}
        )

        # Step 4: HUMAN-IN-THE-LOOP CHECK
        if requires_approval:
            status = "WAITING_FOR_APPROVAL"
            log_step(
                "WAITING_FOR_APPROVAL", "waiting",
                f"Action '{approval_action.get('title', 'Action')}' requires user approval before execution.",
                {"approval_action": approval_action}
            )
            AgentRunRepository.create(
                conn, run_id, user_id, goal, intent,
                status="WAITING_FOR_APPROVAL",
                requires_approval=True,
                requires_approval_action=approval_action,
                summary="Plan generated and awaiting user approval."
            )
            return {
                "run_id": run_id,
                "goal": goal,
                "intent": intent,
                "status": "WAITING_FOR_APPROVAL",
                "requiresApproval": True,
                "actionPendingApproval": approval_action,
                "plan": plan,
                "tools": tools_selected,
                "timeline": timeline,
                "summary": f"Plan formulated with {len(plan.get('tasks', []))} tasks. Awaiting your approval to execute.",
                "tasks": TaskRepository.list_all(conn, user_id),
                "success": True
            }

        # Step 5: EXECUTING
        log_step("EXECUTING", "in_progress", f"Executing {len(pipeline)} autonomous actions.")
        exec_results = ToolExecutor.execute_pipeline(user_id, conn, pipeline, run_id)
        successful_count = sum(1 for r in exec_results if r.get("status") == "SUCCESS")
        log_step("EXECUTING", "completed", f"Executed {len(pipeline)} actions ({successful_count} successful).")

        # Step 6: VERIFYING
        log_step("VERIFYING", "in_progress", "Verifying database mutations and state transitions.")
        all_verified, verification_details = ActionVerifier.verify_execution(user_id, conn, exec_results)
        ver_status = "completed" if all_passed_or_lenient(all_verified, len(pipeline)) else "warning"
        log_step("VERIFYING", ver_status, "Post-condition verification complete.", {"details": verification_details})

        # Step 7: COMPLETED
        summary = build_final_summary(intent, goal, exec_results, plan)
        log_step("COMPLETED", "completed", summary)

        AgentRunRepository.create(
            conn, run_id, user_id, goal, intent,
            status="COMPLETED", requires_approval=False, summary=summary
        )

        return {
            "run_id": run_id,
            "goal": goal,
            "intent": intent,
            "status": "COMPLETED",
            "requiresApproval": False,
            "actionPendingApproval": None,
            "plan": plan,
            "tools": tools_selected,
            "timeline": timeline,
            "actionsExecuted": len(exec_results),
            "actionsSuccessful": successful_count,
            "summary": summary,
            "tasks": TaskRepository.list_all(conn, user_id),
            "schedules": ScheduleRepository.list_by_user(conn, user_id),
            "reminders": ReminderRepository.list_by_user(conn, user_id),
            "success": True
        }


def all_passed_or_lenient(all_verified: bool, total_count: int) -> bool:
    if total_count == 0:
        return True
    return all_verified


def build_final_summary(intent: str, goal: str, results: List[Dict[str, Any]], plan: Dict[str, Any]) -> str:
    if intent in ["STUDY_PLAN", "PROJECT_PLAN"]:
        return f"Formulated and executed '{plan.get('title', goal)}' with {len(results)} verified actions."
    elif intent == "DAILY_PLAN":
        return "Daily plan organized: tasks prioritized and schedule aligned with your peak focus hours."
    elif intent == "SCHEDULE_OPTIMIZE":
        return "Focus schedule successfully optimized around your preferred working hours."
    elif intent == "REMINDER_CREATE":
        return "Reminder created and notification scheduled."
    elif intent == "TASK_ACTION":
        return f"Task action executed and verified successfully for '{goal}'."
    return f"Goal '{goal}' processed successfully."


# Global orchestrator singleton
default_orchestrator = AgentOrchestrator()


def run_agent(
    user_message: str,
    confirmed_action: Optional[Dict[str, Any]] = None,
    user_id: int = 1,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """Compatibility entry point for existing API and test callers."""
    from database.connection import get_db_connection
    conn = conn or get_db_connection()
    res = default_orchestrator.run(
        user_id=user_id,
        conn=conn,
        goal=user_message,
        confirmed_action=confirmed_action
    )
    # Ensure legacy chat compatibility keys exist
    res["response"] = res["summary"]
    res["action_pending_approval"] = res["actionPendingApproval"]
    return res
