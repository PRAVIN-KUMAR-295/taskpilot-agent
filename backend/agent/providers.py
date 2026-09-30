from abc import ABC, abstractmethod
import json
import logging
from typing import Dict, Any, List, Optional
try:
    from config import (
        AWS_REGION,
        BEDROCK_MODEL_ID,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        is_bedrock_configured,
        AI_PROVIDER
    )
except ImportError:
    from backend.config import (
        AWS_REGION,
        BEDROCK_MODEL_ID,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY,
        is_bedrock_configured,
        AI_PROVIDER
    )


logger = logging.getLogger("TaskPilot.AIProvider")


class AIProvider(ABC):
    """Abstract interface for TaskPilot AI reasoning providers."""

    @abstractmethod
    def analyze_intent(self, goal: str, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Classify user intent and extract goal entities."""
        pass

    @abstractmethod
    def generate_plan(self, goal: str, intent_data: Dict[str, Any], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured subtasks and scheduling plan."""
        pass


class LocalProvider(AIProvider):
    """
    Deterministic, high-speed heuristic provider.
    Runs locally with zero external network dependencies or API keys.
    Guarantees instant, flawless hackathon demo execution.
    """

    def analyze_intent(self, goal: str, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        g = goal.strip().lower()

        # Check for memory update
        if any(w in g for w in ["i prefer", "my preferred", "remember that", "set my working hours"]):
            return {
                "intent": "MEMORY_UPDATE",
                "goal": goal,
                "confidence": 0.95,
                "entities": {"raw": goal}
            }

        # Check for study plan (AWS exam, certifications, course study)
        if any(w in g for w in ["study plan", "exam", "prepare for", "aws", "certification", "cert"]):
            return {
                "intent": "STUDY_PLAN",
                "goal": goal,
                "confidence": 0.98,
                "entities": {
                    "topic": "AWS Certification" if "aws" in g else "General Study",
                    "duration_days": 7
                }
            }

        # Check for hackathon / project plan
        if any(w in g for w in ["hackathon", "project", "break this project", "submission", "finish everything", "presentation"]):
            return {
                "intent": "PROJECT_PLAN",
                "goal": goal,
                "confidence": 0.96,
                "entities": {
                    "scope": "Hackathon / Project Milestone",
                    "deadline": "Friday" if "friday" in g else "Soon"
                }
            }

        # Check for daily planning
        if any(w in g for w in ["plan my day", "daily plan", "organize my tasks", "prioritize my tasks", "today's focus"]):
            return {
                "intent": "DAILY_PLAN",
                "goal": goal,
                "confidence": 0.94,
                "entities": {"timeframe": "Today"}
            }

        # Check for schedule optimization
        if any(w in g for w in ["optimize my schedule", "reschedule", "reorganize calendar", "optimize schedule"]):
            return {
                "intent": "SCHEDULE_OPTIMIZE",
                "goal": goal,
                "confidence": 0.95,
                "entities": {}
            }

        # Check for reminder creation
        if any(w in g for w in ["remind me", "reminder", "alarm"]):
            return {
                "intent": "REMINDER_CREATE",
                "goal": goal,
                "confidence": 0.95,
                "entities": {"text": goal}
            }

        # Check for direct task CRUD
        if any(w in g for w in ["create task", "add task", "delete task", "complete task", "show tasks", "list tasks"]):
            action = "create"
            if "delete" in g:
                action = "delete"
            elif "complete" in g or "done" in g:
                action = "complete"
            elif "list" in g or "show" in g:
                action = "list"
            return {
                "intent": "TASK_ACTION",
                "goal": goal,
                "confidence": 0.92,
                "entities": {"action": action}
            }

        # Check for knowledge query
        if any(w in g for w in ["search", "what is", "how to", "explain", "knowledge"]):
            return {
                "intent": "SEARCH_KNOWLEDGE",
                "goal": goal,
                "confidence": 0.88,
                "entities": {"query": goal}
            }

        # Default fallback
        return {
            "intent": "PROJECT_PLAN",
            "goal": goal,
            "confidence": 0.80,
            "entities": {"general": True}
        }

    def generate_plan(self, goal: str, intent_data: Dict[str, Any], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        intent = intent_data.get("intent", "PROJECT_PLAN")
        g = goal.lower()

        # Incorporate memory preferences
        work_hours = memory_context.get("preferred_working_hours", "09:00 AM - 06:00 PM")
        evening_focus = memory_context.get("preferred_evening_focus", "07:00 PM - 09:00 PM")

        if intent == "STUDY_PLAN" or "aws" in g:
            tasks = [
                {"title": "Day 1: AWS Cloud Concepts & Global Infrastructure", "priority": "HIGH", "estimated_minutes": 60, "day_or_stage": "Day 1", "dependencies": []},
                {"title": "Day 2: AWS IAM, Security Policies & Cognito", "priority": "URGENT", "estimated_minutes": 75, "day_or_stage": "Day 2", "dependencies": ["Day 1"]},
                {"title": "Day 3: Compute Architecture - EC2, Lambda & ECS", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Day 3", "dependencies": ["Day 2"]},
                {"title": "Day 4: Storage & Databases - S3, EBS, DynamoDB", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Day 4", "dependencies": ["Day 3"]},
                {"title": "Day 5: Networking & Edge - VPC, API Gateway, CloudFront", "priority": "MEDIUM", "estimated_minutes": 75, "day_or_stage": "Day 5", "dependencies": ["Day 4"]},
                {"title": "Day 6: Amazon Bedrock & AI Services Integration", "priority": "HIGH", "estimated_minutes": 60, "day_or_stage": "Day 6", "dependencies": ["Day 5"]},
                {"title": "Day 7: Full Practice Exam & Knowledge Revision", "priority": "URGENT", "estimated_minutes": 120, "day_or_stage": "Day 7", "dependencies": ["Day 6"]}
            ]
            return {
                "goal": goal,
                "title": "7-Day AWS Preparation & Mastery Blueprint",
                "estimated_days": 7,
                "total_tasks": len(tasks),
                "tasks": tasks,
                "scheduling_strategy": f"Scheduled in evening focus windows ({evening_focus}) based on user profile memory."
            }

        elif intent == "DAILY_PLAN" or "day" in g or "prioritize" in g:
            tasks = [
                {"title": "Morning Triage: Review Urgent Deadlines & Objectives", "priority": "URGENT", "estimated_minutes": 25, "day_or_stage": "09:00 AM", "dependencies": []},
                {"title": "Deep Work Sprint: Critical Path Feature Implementation", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "09:30 AM", "dependencies": []},
                {"title": "Architecture Review & Automated Verification Pass", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "11:15 AM", "dependencies": []},
                {"title": "Midday Sync & External Communications", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "02:00 PM", "dependencies": []},
                {"title": "Wrap-up, Documentation & Evening Review", "priority": "LOW", "estimated_minutes": 30, "day_or_stage": "05:00 PM", "dependencies": []}
            ]
            return {
                "goal": goal,
                "title": "Daily Priority Alignment Plan",
                "estimated_days": 1,
                "total_tasks": len(tasks),
                "tasks": tasks,
                "scheduling_strategy": f"Aligned with preferred working hours ({work_hours})."
            }

        elif intent == "PROJECT_PLAN" or "hackathon" in g or "friday" in g:
            tasks = [
                {"title": "Finalize Core Application Logic & Autonomous Agents", "priority": "URGENT", "estimated_minutes": 90, "day_or_stage": "Phase 1", "dependencies": []},
                {"title": "End-to-End System Testing & Verifier Calibration", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Phase 2", "dependencies": ["Phase 1"]},
                {"title": "Record High-Definition Demo Walkthrough", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Phase 3", "dependencies": ["Phase 2"]},
                {"title": "Prepare Pitch Presentation Slides (PPT)", "priority": "URGENT", "estimated_minutes": 60, "day_or_stage": "Phase 4", "dependencies": ["Phase 2"]},
                {"title": "Review Architecture Documentation & README", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "Phase 5", "dependencies": ["Phase 4"]},
                {"title": "Final Submission Verification & Link Validation", "priority": "URGENT", "estimated_minutes": 20, "day_or_stage": "Phase 6", "dependencies": ["Phase 5"]}
            ]
            return {
                "goal": goal,
                "title": "End-to-End Delivery Milestone Plan",
                "estimated_days": 2,
                "total_tasks": len(tasks),
                "tasks": tasks,
                "scheduling_strategy": "Aggressive prioritization for upcoming deadline."
            }

        else:
            tasks = [
                {"title": f"Define Specifications: {goal}", "priority": "HIGH", "estimated_minutes": 45, "day_or_stage": "Stage 1", "dependencies": []},
                {"title": "Execute Core Task Components", "priority": "HIGH", "estimated_minutes": 90, "day_or_stage": "Stage 2", "dependencies": ["Stage 1"]},
                {"title": "Quality Verification & Audit", "priority": "MEDIUM", "estimated_minutes": 30, "day_or_stage": "Stage 3", "dependencies": ["Stage 2"]}
            ]
            return {
                "goal": goal,
                "title": f"Structured Execution Plan: {goal}",
                "estimated_days": 1,
                "total_tasks": len(tasks),
                "tasks": tasks,
                "scheduling_strategy": "Standard sequential execution."
            }


class BedrockProvider(AIProvider):
    """
    AWS Bedrock integration provider.
    Uses boto3 bedrock-runtime to invoke Claude or Titan models server-side.
    Falls back gracefully to LocalProvider if credentials or region are unavailable.
    """

    def __init__(self):
        self.fallback = LocalProvider()
        self._client = None
        if is_bedrock_configured():
            try:
                import boto3
                kwargs = {"region_name": AWS_REGION}
                if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
                    kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
                    kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
                self._client = boto3.client("bedrock-runtime", **kwargs)
                logger.info(f"Initialized AWS Bedrock client in region: {AWS_REGION}")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS Bedrock client: {e}. Falling back to LocalProvider.")
                self._client = None

    def analyze_intent(self, goal: str, memory_context: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            return self.fallback.analyze_intent(goal, memory_context)

        try:
            prompt = f"Analyze user goal: '{goal}'. Memory: {json.dumps(memory_context)}. Return JSON with keys: intent, goal, confidence, entities."
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [{"role": "user", "content": prompt}]
            })
            response = self._client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=body
            )
            resp_body = json.loads(response["body"].read())
            raw_text = resp_body["content"][0]["text"]
            return json.loads(raw_text)
        except Exception as e:
            logger.warning(f"Bedrock invocation failed ({e}), using LocalProvider.")
            return self.fallback.analyze_intent(goal, memory_context)

    def generate_plan(self, goal: str, intent_data: Dict[str, Any], memory_context: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            return self.fallback.generate_plan(goal, intent_data, memory_context)

        try:
            prompt = f"Create structured plan for goal '{goal}'. Intent: {json.dumps(intent_data)}. Memory: {json.dumps(memory_context)}. Return JSON with keys: goal, title, estimated_days, total_tasks, tasks, scheduling_strategy."
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            })
            response = self._client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=body
            )
            resp_body = json.loads(response["body"].read())
            raw_text = resp_body["content"][0]["text"]
            return json.loads(raw_text)
        except Exception as e:
            logger.warning(f"Bedrock plan generation failed ({e}), using LocalProvider.")
            return self.fallback.generate_plan(goal, intent_data, memory_context)


def get_ai_provider() -> AIProvider:
    """Returns the configured AI Provider based on settings and environment."""
    if AI_PROVIDER == "bedrock" and is_bedrock_configured():
        return BedrockProvider()
    return LocalProvider()
