import sqlite3
from typing import Dict, Any, List
from .base import BaseTool, ToolResult

# Curated knowledge base for everyday tasks, productivity frameworks, and exam prep
KNOWLEDGE_BASE = [
    {
        "keywords": ["aws", "cloud", "exam", "solutions architect", "practitioner"],
        "title": "AWS Certification Blueprint & Preparation Guide",
        "snippet": "AWS Certifications require mastery across 5 core pillars: IAM Security, Compute (EC2, ECS, Lambda), Storage & DB (S3, EBS, DynamoDB, RDS), Networking (VPC, Route53, CloudFront), and Monitoring (CloudWatch, CloudTrail). Effective preparation requires 7 days of structured daily module study followed by practice exams."
    },
    {
        "keywords": ["hackathon", "pitch", "demo", "presentation", "submission"],
        "title": "Hackathon Winning Strategy Guide",
        "snippet": "Successful hackathon submissions follow the Problem-Solution-Demo-Architecture framework. Allocate 40% time to core functionality, 20% to edge-case testing, 20% to documentation/visuals, and 20% to rehearsing an engaging demo video."
    },
    {
        "keywords": ["prioritize", "eisenhower", "productivity", "focus", "time"],
        "title": "Eisenhower Matrix & Cognitive Load Optimization",
        "snippet": "Tasks should be categorized into 4 quadrants: Urgent & Important (immediate action), Important but Not Urgent (scheduled focus blocks), Urgent but Not Important (automate/delegate), and Neither (eliminate). High-leverage work is optimal in 90-minute morning deep work blocks."
    },
    {
        "keywords": ["study", "pomodoro", "retention", "spaced repetition"],
        "title": "Active Recall & Spaced Repetition Protocol",
        "snippet": "Optimal study performance combines 50-minute focused review with 10-minute active recall quizzes. Schedule high-cognitive load sessions during peak energy hours (morning or designated evening study windows)."
    }
]


class SearchKnowledgeTool(BaseTool):
    name = "search_knowledge_tool"
    description = "Retrieve relevant application and productivity domain knowledge to assist with planning and task execution."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic or keywords to look up in the knowledge base."
            }
        },
        "required": ["query"]
    }

    def execute(self, user_id: int, conn: sqlite3.Connection, **kwargs) -> ToolResult:
        valid, err = self.validate_input(kwargs)
        if not valid:
            return ToolResult(success=False, error=err, message=err)

        query = kwargs.get("query", "").lower()
        query_words = set(query.split())

        matches = []
        for doc in KNOWLEDGE_BASE:
            score = 0
            for kw in doc["keywords"]:
                if kw in query or any(kw in word for word in query_words):
                    score += 2
            for word in query_words:
                if len(word) > 3 and word in doc["snippet"].lower():
                    score += 1
            if score > 0:
                matches.append((score, doc))

        matches.sort(key=lambda x: x[0], reverse=True)
        results = [m[1] for m in matches[:3]]

        if not results:
            # Fallback general productivity guidance
            results = [{
                "title": "TaskPilot Autonomous Best Practice",
                "snippet": f"For '{query}': decompose goal into distinct tasks, assign clear priorities (URGENT/HIGH), and establish calendar focus blocks."
            }]

        return ToolResult(
            success=True,
            data=results,
            message=f"Found {len(results)} relevant knowledge articles for '{query}'."
        )
