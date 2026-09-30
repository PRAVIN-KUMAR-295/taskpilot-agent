import sqlite3
import datetime
from typing import Dict, Any, Tuple, Optional
from .base import BaseTool, ToolResult


class GmailTool(BaseTool):
    name = "gmail_tool"
    description = "Send emails or draft messages via Gmail. [Demo / Simulated Tool]"
    is_simulated = True
    requires_confirmation_by_default = True
    input_schema = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Email message body"}
        },
        "required": ["to", "subject", "body"]
    }

    def check_requires_confirmation(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        to = params.get("to", "recipient")
        subj = params.get("subject", "Task Reminder")
        return True, f"Send email to '{to}' with subject '{subj}'? [External side-effect confirmation required]"

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        to = kwargs.get("to")
        subject = kwargs.get("subject")
        body = kwargs.get("body")
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        simulated_data = {
            "status": "SIMULATED_SENT",
            "provider": "Gmail API (Simulated)",
            "to": to,
            "subject": subject,
            "sent_at": timestamp
        }
        return ToolResult(
            success=True,
            data=simulated_data,
            message=f"[Demo / Simulated Tool] Email sent to {to} with subject: '{subject}'."
        )


class SlackTool(BaseTool):
    name = "slack_tool"
    description = "Post updates or reminders to a Slack channel. [Demo / Simulated Tool]"
    is_simulated = True
    requires_confirmation_by_default = True
    input_schema = {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Slack channel name (e.g. #general, #hackathon)"},
            "message": {"type": "string", "description": "Message content to post"}
        },
        "required": ["channel", "message"]
    }

    def check_requires_confirmation(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        channel = params.get("channel", "#general")
        return True, f"Broadcast message to Slack channel '{channel}'? [Public communication confirmation required]"

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        channel = kwargs.get("channel")
        msg = kwargs.get("message")
        return ToolResult(
            success=True,
            data={"channel": channel, "status": "SIMULATED_POSTED"},
            message=f"[Demo / Simulated Tool] Message posted to Slack channel '{channel}'."
        )


class GoogleCalendarTool(BaseTool):
    name = "google_calendar_tool"
    description = "Sync and schedule events to Google Calendar. [Demo / Simulated Tool]"
    is_simulated = True
    requires_confirmation_by_default = False
    input_schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Calendar event summary"},
            "start_time": {"type": "string", "description": "Event start time"},
            "end_time": {"type": "string", "description": "Event end time"},
            "description": {"type": "string", "description": "Event description"}
        },
        "required": ["summary", "start_time", "end_time"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        summary = kwargs.get("summary")
        start = kwargs.get("start_time")
        end = kwargs.get("end_time")

        return ToolResult(
            success=True,
            data={
                "event_id": "gcal_sim_892341",
                "summary": summary,
                "start": start,
                "end": end,
                "status": "SIMULATED_SYNCED"
            },
            message=f"[Demo / Simulated Tool] Synced '{summary}' ({start} - {end}) to Google Calendar."
        )


class NotionTool(BaseTool):
    name = "notion_tool"
    description = "Export and sync tasks to Notion database. [Demo / Simulated Tool]"
    is_simulated = True
    input_schema = {
        "type": "object",
        "properties": {
            "page_title": {"type": "string", "description": "Title of Notion page/database entry"},
            "content": {"type": "string", "description": "Markdown content to sync"}
        },
        "required": ["page_title"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        title = kwargs.get("page_title")
        return ToolResult(
            success=True,
            data={"page_id": "notion_sim_4812", "title": title, "status": "SIMULATED_SYNCED"},
            message=f"[Demo / Simulated Tool] Exported '{title}' to Notion workspace."
        )


class OutlookTool(BaseTool):
    name = "outlook_tool"
    description = "Sync calendar appointments with Microsoft Outlook. [Demo / Simulated Tool]"
    is_simulated = True
    input_schema = {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Appointment subject"},
            "start": {"type": "string", "description": "Start time"},
            "end": {"type": "string", "description": "End time"}
        },
        "required": ["subject", "start", "end"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        subject = kwargs.get("subject")
        return ToolResult(
            success=True,
            data={"outlook_id": "ms_out_5129", "subject": subject, "status": "SIMULATED_SYNCED"},
            message=f"[Demo / Simulated Tool] Synced appointment '{subject}' with Microsoft Outlook."
        )


class TodoistTool(BaseTool):
    name = "todoist_tool"
    description = "Export tasks to Todoist. [Demo / Simulated Tool]"
    is_simulated = True
    input_schema = {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "Task content in Todoist"},
            "priority": {"type": "integer", "description": "Todoist priority 1-4"}
        },
        "required": ["content"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        content = kwargs.get("content")
        return ToolResult(
            success=True,
            data={"todoist_id": "todoist_sim_9104", "content": content, "status": "SIMULATED_SYNCED"},
            message=f"[Demo / Simulated Tool] Task '{content}' created in Todoist."
        )
