import os
from pathlib import Path
from dotenv import load_dotenv

# Project root = taskpilot-agent/
BASE_DIR = Path(__file__).resolve().parent.parent

# Load root .env
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

if not OPENAI_API_KEY:
    raise RuntimeError(
        f"OPENAI_API_KEY is missing. Checked: {ENV_FILE}"
    )