import sqlite3
from typing import Dict, Any, List
from .base import BaseTool, ToolResult
try:
    from database.repositories import PlanRepository, MemoryRepository
except ImportError:
    from backend.database.repositories import PlanRepository, MemoryRepository




class PlanningTool(BaseTool):
    name = "planning_tool"
    description = "Deconstruct high-level goals into subtasks, estimate effort, assign priorities, and generate structured execution plans."
    input_schema = {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "High-level goal statement (e.g. 'Prepare for AWS exam', 'Hackathon submission')."
            },
            "subtasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "priority": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "URGENT"]},
                        "estimated_minutes": {"type": "integer"},
                        "day_or_stage": {"type": "string"},
                        "dependencies": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["title", "priority"]
                },
                "description": "Optional explicit subtask breakdown if already decomposed."
            },
            "estimated_days": {
                "type": "integer",
                "description": "Target duration in days (default: 7)."
            }
        },
        "required": ["goal"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        goal = kwargs.get("goal", "").strip()
        subtasks = kwargs.get("subtasks")
        estimated_days = int(kwargs.get("estimated_days", 7))

        try:
            # Check user memory for study/work preferences
            memories = MemoryRepository.get_all(conn, user_id)
            pref_map = {m["key"]: m["value"] for m in memories}

            # If no explicit subtasks were passed, decompose intelligently using domain heuristics
            if not subtasks:
                lower = goal.lower()
                if "aws" in lower or "exam" in lower or "cert" in lower:
                    subtasks = [
                        {"title": "Day 1: Cloud Concepts & Global Infrastructure", "priority": "HIGH", "estimated_minutes": 60, "day_or_stage": "Day 1", "dependencies": []},
                        {"title": "Day 2: AWS IAM, Policies & Security Governance", "priority": "URGENT", "estimated_minutes": 75, "day_or_stage": "Day 2", "dependencies": ["Day 1"]},
                        {"title": "Day 3: Compute - EC2, Auto Scaling, ECS & Lambda", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Day 3", "dependencies": ["Day 2"]},
                        {"title": "Day 4: Storage & Databases - S3, EBS, RDS & DynamoDB", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Day 4", "dependencies": ["Day 3"]},
                        {"title": "Day 5: Networking & Content Delivery - VPC, Route 53, CloudFront", "priority": "MEDIUM", "estimated_minutes": 75, "day_or_stage": "Day 5", "dependencies": ["Day 4"]},
                        {"title": "Day 6: Monitoring, Billing & Well-Architected Framework", "priority": "MEDIUM", "estimated_minutes": 60, "day_or_stage": "Day 6", "dependencies": ["Day 5"]},
                        {"title": "Day 7: Full Practice Exam & Weak-Area Revision", "priority": "URGENT", "estimated_minutes": 120, "day_or_stage": "Day 7", "dependencies": ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6"]},
                    ]
                    estimated_days = 7

                elif "hackathon" in lower or "ppt" in lower or "submission" in lower:
                    subtasks = [
                        {"title": "Finalize Core Application & Autonomous Features", "priority": "URGENT", "estimated_minutes": 90, "day_or_stage": "Phase 1", "dependencies": []},
                        {"title": "End-to-End System Testing & Edge Case Verification", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Phase 2", "dependencies": ["Phase 1"]},
                        {"title": "Record High-Impact Demo Video", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Phase 3", "dependencies": ["Phase 2"]},
                        {"title": "Prepare Hackathon Pitch PPT & Slide Deck", "priority": "URGENT", "estimated_minutes": 60, "day_or_stage": "Phase 4", "dependencies": ["Phase 2"]},
                        {"title": "Review Architecture Documentation & README", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "Phase 5", "dependencies": ["Phase 4"]},
                        {"title": "Submit Final Project & Verify Submission Links", "priority": "URGENT", "estimated_minutes": 15, "day_or_stage": "Phase 6", "dependencies": ["Phase 5"]},
                    ]
                    estimated_days = 2

                elif "day" in lower or "daily" in lower or "today" in lower:
                    subtasks = [
                        {"title": "Review High-Priority Deadlines & Clear Critical Path", "priority": "URGENT", "estimated_minutes": 30, "day_or_stage": "Morning", "dependencies": []},
                        {"title": "Deep Work Sprint: Core Deliverable Development", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Morning Slot", "dependencies": []},
                        {"title": "Communications & Team Sync", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "Midday", "dependencies": []},
                        {"title": "Secondary Focus Block & Review", "priority": "MEDIUM", "estimated_minutes": 60, "day_or_stage": "Afternoon", "dependencies": []},
                        {"title": "Evening Status Check & Plan Tomorrow", "priority": "LOW", "estimated_minutes": 20, "day_or_stage": "Evening", "dependencies": []},
                    ]
                    estimated_days = 1

                else:
                    # General project deconstruction
                    subtasks = [
                        {"title": f"Define Scope & Requirements for {goal}", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Step 1", "dependencies": []},
                        {"title": f"Develop Milestone 1 Implementation", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Step 2", "dependencies": ["Step 1"]},
                        {"title": f"Test & Verify Deliverables", "priority": "MEDIUM", "estimated_minutes": 45, "day_or_stage": "Step 3", "dependencies": ["Step 2"]},
                        {"title": f"Review Final Output & Documentation", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "Step 4", "dependencies": ["Step 3"]},
                    ]
                    estimated_days = 3

            plan_dict = {
                "goal": goal,
                "estimated_days": estimated_days,
                "total_tasks": len(subtasks),
                "tasks": subtasks,
                "user_preferences_factored": {
                    "preferred_working_hours": pref_map.get("preferred_working_hours", "09:00 - 18:00"),
                    "evening_focus": pref_map.get("preferred_evening_focus", "19:00 - 21:00")
                }
            }

            plan_record = PlanRepository.create(
                conn=conn,
                user_id=user_id,
                goal=goal,
                plan_data=plan_dict,
                status="DRAFT",
                total_tasks=len(subtasks),
                estimated_days=estimated_days
            )

            return ToolResult(
                success=True,
                data=plan_record,
                message=f"Generated structured plan with {len(subtasks)} tasks across {estimated_days} days for: '{goal}'."
            )

        except Exception as e:
            return ToolResult(success=False, error=str(e), message=f"PlanningTool error: {str(e)}")
