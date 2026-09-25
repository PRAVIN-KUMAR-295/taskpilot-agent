def test_tools_import():

    from backend.tools import (
        tool_get_tasks,
        tool_create_task,
        tool_complete_task,
        tool_search
    )

    assert callable(tool_get_tasks)
    assert callable(tool_create_task)
    assert callable(tool_complete_task)
    assert callable(tool_search)