import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = taskpilot-agent/
BASE_DIR = Path(__file__).resolve().parent.parent

# Load root .env
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# Server Config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Security & JWT
JWT_SECRET = os.getenv("JWT_SECRET", "taskpilot-agent-super-secret-jwt-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))  # 24 hours

# Database
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "taskpilot.db"))

# AWS Bedrock Config (Server-side only)
AWS_REGION = os.getenv("AWS_REGION", "us-east-1").strip()
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0").strip()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

# OpenAI Config (Optional fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
MODEL_NAME = OPENAI_MODEL

# AI Provider preference: "bedrock", "openai", "local", or "auto"
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()


def is_bedrock_configured() -> bool:
    """Return True if AWS credentials or Bedrock environment variables are configured."""
    return bool(AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY) or bool(os.getenv("AWS_PROFILE"))


def is_openai_configured() -> bool:
    """Return True if OPENAI_API_KEY is present and not dummy."""
    return bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("dummy")