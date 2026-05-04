from google.adk.agents import Agent

from sadify_agent.agent import root_agent


def test_root_agent_is_adk_agent_with_expected_identity():
    assert isinstance(root_agent, Agent)
    assert root_agent.name == "sadify"
    assert root_agent.model == "gemini-2.5-flash"
    assert "clarification" in root_agent.instruction.lower()
    assert "system analysis and design" in root_agent.instruction.lower()
