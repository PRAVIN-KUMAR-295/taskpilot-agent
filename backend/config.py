import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = taskpilot-agent/
BASE_DIR = Path(__file__).resolve().parent.parent

# Load root .env
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def is_openai_configured() -> bool:
    """Return True if OPENAI_API_KEY is present and not empty."""
    return bool(OPENAI_API_KEY)