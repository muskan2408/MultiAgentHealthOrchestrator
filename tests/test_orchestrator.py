"""
Tests for Orchestrator — end-to-end flow, session management, delegation.
Run with: pytest tests/test_orchestrator.py -v
"""
from unittest.mock import MagicMock, patch

from src.models.schemas import AgentType, UserMessage
from src.orchestrator.orchestrator import Orchestrator, FALLBACK_RESPONSE


class TestOrchestrator:
    # NOTE: @patch decorators apply bottom-up.
    # Bottom decorator → first argument, top decorator → second argument.

    @patch("src.agents.router_agent.litellm.completion")   # second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # first  → mock_base_llm
    def test_full_flow_symptom(self, mock_base_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "pain", "confidence": 0.9}'))]
        )
        mock_base_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Tell me more about your headache."))]
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="I have a headache", session_id="s1"))
        assert response.agent == AgentType.SYMPTOM
        assert len(response.text) > 0

    @patch("src.agents.router_agent.litellm.completion")   # second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # first  → mock_base_llm
    def test_full_flow_medication(self, mock_base_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "medication", "reasoning": "drug", "confidence": 0.9}'))]
        )
        mock_base_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Ibuprofen info here."))]
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="Tell me about ibuprofen", session_id="s2"))
        assert response.agent == AgentType.MEDICATION

    @patch("src.agents.router_agent.litellm.completion")
    def test_fallback_response(self, mock_router_llm):
        mock_router_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "fallback", "reasoning": "off topic", "confidence": 0.99}'))]
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="Who won the World Cup?", session_id="s3"))
        assert response.agent == AgentType.FALLBACK
        assert response.text == FALLBACK_RESPONSE

    @patch("src.agents.router_agent.litellm.completion")   # second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # first  → mock_base_llm
    def test_context_persists_across_turns(self, mock_base_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "symptom", "reasoning": "pain", "confidence": 0.9}'))]
        )
        mock_base_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Noted."))]
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Turn 1", session_id="persist"))
        orch.process(UserMessage(text="Turn 2", session_id="persist"))
        ctx = orch._contexts["persist"]
        assert len(ctx.history) == 4  # 2 user + 2 assistant

    @patch("src.agents.router_agent.litellm.completion")   # second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # first  → mock_base_llm
    def test_different_sessions_are_isolated(self, mock_base_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "lifestyle", "reasoning": "diet", "confidence": 0.85}'))]
        )
        mock_base_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Eat well."))]
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Hello", session_id="userA"))
        orch.process(UserMessage(text="Hello", session_id="userB"))
        assert "userA" in orch._contexts
        assert "userB" in orch._contexts
        assert orch._contexts["userA"] is not orch._contexts["userB"]

    @patch("src.agents.router_agent.litellm.completion")   # second → mock_agent_llm
    @patch("src.agents.base_agent.litellm.completion")     # first  → mock_base_llm
    def test_new_session_created_automatically(self, mock_base_llm, mock_agent_llm):
        mock_agent_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"target_agent": "lifestyle", "reasoning": "diet", "confidence": 0.8}'))]
        )
        mock_base_llm.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Sure!"))]
        )
        orch = Orchestrator()
        assert "brand-new" not in orch._contexts
        orch.process(UserMessage(text="Hi", session_id="brand-new"))
        assert "brand-new" in orch._contexts

    def test_clear_session_removes_context(self):
        orch = Orchestrator()
        orch._contexts["to-clear"] = MagicMock()
        orch.clear_session("to-clear")
        assert "to-clear" not in orch._contexts

    def test_get_all_sessions(self):
        orch = Orchestrator()
        orch._contexts["a"] = MagicMock()
        orch._contexts["b"] = MagicMock()
        sessions = orch.get_all_sessions()
        assert "a" in sessions
        assert "b" in sessions
