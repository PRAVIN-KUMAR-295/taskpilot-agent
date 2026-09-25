from services.task_service import (
    get_tasks,
    create_task,
    complete_task
)

from services.search_service import (
    search_information
)


def tool_get_tasks():

    return get_tasks()


def tool_create_task(
    title,
    priority
):

    return create_task(
        title,
        priority
    )


def tool_complete_task(
    task_id
):

    task = complete_task(task_id)

    if task is None:

        return {
            "success": False,
            "message": "Task not found."
        }

    return {
        "success": True,
        "task": task
    }


def tool_search(query):

    return search_information(query)