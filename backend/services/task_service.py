import json
from pathlib import Path
from datetime import datetime


DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "tasks.json"
)


def load_tasks():

    if not DATA_FILE.exists():
        return []

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:
        return []


def save_tasks(tasks):

    DATA_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            tasks,
            file,
            indent=2,
            ensure_ascii=False
        )


def get_tasks():

    return load_tasks()


def create_task(title, priority):

    tasks = load_tasks()

    if tasks:

        next_id = max(
            task["id"]
            for task in tasks
        ) + 1

    else:

        next_id = 1

    task = {
        "id": next_id,
        "title": title,
        "priority": priority,
        "completed": False,
        "created_at": datetime.now().isoformat()
    }

    tasks.append(task)

    save_tasks(tasks)

    return task


def complete_task(task_id):

    tasks = load_tasks()

    for task in tasks:

        if task["id"] == task_id:

            task["completed"] = True

            save_tasks(tasks)

            return task

    return None