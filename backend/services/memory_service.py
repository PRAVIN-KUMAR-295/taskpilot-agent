import json
from pathlib import Path


MEMORY_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "memory.json"
)


def load_memory():

    if not MEMORY_FILE.exists():
        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return []


def save_memory(
    user_message,
    assistant_response
):

    memories = load_memory()

    memories.append({
        "user": user_message,
        "assistant": assistant_response
    })

    memories = memories[-20:]

    MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memories,
            file,
            indent=2,
            ensure_ascii=False
        )


def get_recent_memory(limit=5):

    memories = load_memory()

    return memories[-limit:]