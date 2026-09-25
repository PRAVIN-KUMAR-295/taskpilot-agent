def test_agent_import():

    from backend.agent import run_agent

    assert callable(run_agent)