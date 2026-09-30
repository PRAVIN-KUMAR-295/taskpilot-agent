from typing import Tuple, List, Dict, Any, Optional
try:
    from tools.registry import default_registry
except ImportError:
    from backend.tools.registry import default_registry



class ToolSelector:
    """Selects the sequence of tools required to achieve a goal and enforces human-in-the-loop safety."""

    @staticmethod
    def select_tools(
        intent: str,
        goal: str,
        plan: Dict[str, Any],
        entities: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], bool, Dict[str, Any]]:
        """
        Returns:
            - tool_pipeline: List of tool invocation specs [{"tool_name": "...", "params": {...}}]
            - requires_approval: bool
            - approval_action: Dict with prompt and payload if confirmation is required
        """
        pipeline: List[Dict[str, Any]] = []
        requires_approval = False
        approval_action: Dict[str, Any] = {}

        if intent in ["STUDY_PLAN", "PROJECT_PLAN"]:
            # Decompose -> create plan -> create tasks -> schedule -> reminders -> notify
            pipeline.append({
                "tool_name": "planning_tool",
                "params": {"goal": goal, "subtasks": plan.get("tasks", [])}
            })
            for t in plan.get("tasks", []):
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {
                        "action": "create",
                        "title": t["title"],
                        "priority": t.get("priority", "MEDIUM"),
                        "estimated_duration": t.get("estimated_minutes", 30),
                        "due_date": t.get("day_or_stage", "Next Days"),
                        "category": "Plan Deliverable"
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
                    "title": f"Review execution milestones for: {goal}",
                    "reminder_time": "Tomorrow at 09:00 AM"
                }
            })
            pipeline.append({
                "tool_name": "notification_tool",
                "params": {
                    "title": f"Plan Generated: {plan.get('title', goal)}",
                    "message": f"Successfully created {len(plan.get('tasks', []))} tasks and optimized focus calendar.",
                    "urgency": "normal"
                }
            })
            # High-level plans have significant side effects (multiple tasks + schedules),
            # so they trigger the Plan Ready approval card unless explicitly pre-confirmed
            requires_approval = True
            approval_action = {
                "type": "APPROVE_PLAN",
                "tool_name": "planning_tool",
                "title": f"Approve Plan: {plan.get('title', goal)}",
                "description": f"Create {len(plan.get('tasks', []))} tasks, optimize focus schedule, and set reminders.",
                "tasks_count": len(plan.get("tasks", [])),
                "plan": plan
            }

        elif intent == "DAILY_PLAN":
            pipeline.append({
                "tool_name": "planning_tool",
                "params": {"goal": goal, "subtasks": plan.get("tasks", [])}
            })
            for t in plan.get("tasks", []):
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {
                        "action": "create",
                        "title": t["title"],
                        "priority": t.get("priority", "HIGH"),
                        "estimated_duration": t.get("estimated_minutes", 30),
                        "due_date": "Today",
                        "category": "Daily Focus"
                    }
                })
            pipeline.append({
                "tool_name": "schedule_tool",
                "params": {"action": "optimize"}
            })
            pipeline.append({
                "tool_name": "notification_tool",
                "params": {
                    "title": "Daily Focus Plan Activated",
                    "message": "Today's schedule has been optimized based on your priority preferences.",
                    "urgency": "normal"
                }
            })

        elif intent == "SCHEDULE_OPTIMIZE":
            pipeline.append({
                "tool_name": "schedule_tool",
                "params": {"action": "optimize"}
            })
            pipeline.append({
                "tool_name": "notification_tool",
                "params": {
                    "title": "Schedule Optimized",
                    "message": "Your focus calendar has been reorganized around your prime working hours.",
                    "urgency": "normal"
                }
            })

        elif intent == "TASK_ACTION":
            action = entities.get("action", "create")
            task_id = entities.get("task_id")

            if action == "delete":
                requires_approval = True
                approval_action = {
                    "type": "DELETE_TASK",
                    "tool_name": "task_tool",
                    "title": f"Confirm Task Deletion (#{task_id})",
                    "description": f"Permanently delete task #{task_id}? This action cannot be reversed.",
                    "params": {"action": "delete", "task_id": task_id}
                }
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {"action": "delete", "task_id": task_id}
                })
            elif action == "complete":
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {"action": "complete", "task_id": task_id}
                })
            elif action == "list":
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {"action": "list"}
                })
            else:
                # Create task
                pipeline.append({
                    "tool_name": "task_tool",
                    "params": {
                        "action": "create",
                        "title": goal.replace("create a task", "").replace("create task", "").replace("add task", "").strip() or goal,
                        "priority": entities.get("priority", "MEDIUM"),
                        "due_date": entities.get("due_date", "Tomorrow")
                    }
                })

        elif intent == "REMINDER_CREATE":
            pipeline.append({
                "tool_name": "reminder_tool",
                "params": {
                    "action": "create",
                    "title": goal.replace("remind me to", "").replace("remind me", "").strip() or goal,
                    "reminder_time": entities.get("due_date", "Tomorrow at 6:00 PM")
                }
            })
            pipeline.append({
                "tool_name": "notification_tool",
                "params": {
                    "title": "Reminder Configured",
                    "message": f"Autonomous alert scheduled for '{goal}'.",
                    "urgency": "high"
                }
            })

        elif intent == "SEARCH_KNOWLEDGE":
            pipeline.append({
                "tool_name": "search_knowledge_tool",
                "params": {"query": entities.get("query", goal)}
            })

        elif intent == "MEMORY_UPDATE":
            # Handled directly in intent analyzer / memory
            pass

        return pipeline, requires_approval, approval_action
