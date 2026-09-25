import json
import re
from pathlib import Path
from typing import List, Dict, Any


MEMORY_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "memory.json"
)

# Regex patterns to detect and scrub API keys and sensitive tokens
SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE),
    re.compile(r'(api[_\-]?key|secret|password|access[_\-]?token)\s*[:=]\s*["\']?[a-zA-Z0-9_\-\.]{8,}["\']?', re.IGNORECASE),
]


def scrub_secrets(text: str) -> str:
    """Mask any detected API keys, tokens, or credentials before storage."""
    if not isinstance(text, str):
        return str(text)

    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def load_memory() -> List[Dict[str, str]]:
    """Load memories from disk."""
    if not MEMORY_FILE.exists():
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def save_memory(user_message: str, assistant_response: str) -> None:
    """Save user and assistant interaction with secret scrubbing."""
    # Do not save empty interactions
    if not user_message and not assistant_response:
        return

    clean_user = scrub_secrets(user_message or "")
    clean_assistant = scrub_secrets(assistant_response or "")

    memories = load_memory()

    memories.append({
        "user": clean_user,
        "assistant": clean_assistant
    })

    # Keep only the last 20 interactions
    memories = memories[-20:]

    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memories, file, indent=2, ensure_ascii=False)


def get_recent_memory(limit: int = 5) -> List[Dict[str, str]]:
    """Retrieve recent conversation context."""
    memories = load_memory()
    return memories[-limit:]


def clear_memory() -> None:
    """Clear memory storage."""
    save_tasks_empty = []
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(save_tasks_empty, file)