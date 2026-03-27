"""
Tests for Orchestrator — end-to-end flow, session management, delegation.
Run with: pytest tests/test_orchestrator.py -v
"""
from unittest.mock import MagicMock, patch

from src.models.schemas import AgentType, UserMessage
from src.orchestrator.orchestrator import Orchestrator, FALLBACK_RESPONSE


def _llm_mock(router_json, agent_text, synth_text=None):
    """Return a side_effect callable that routes LLM calls by inspecting
    the system prompt content: router calls contain 'routing decision',
    synthesizer calls contain the synthesizer prompt, everything else is
    a specialist agent call."""

    def _side_effect(*args, **kwargs):
        messages = kwargs.get("messages") or args[0]
        system = messages[0]["content"].lower() if messages else ""
        if "routing decision" in system or "classify" in system or "router" in system:
            content = router_json
        elif "quality specialist" in system or "refine" in system:
            content = synth_text or agent_text
        else:
            content = agent_text
        return MagicMock(
            choices=[MagicMock(message=MagicMock(content=content))]
        )

    return _side_effect


class TestOrchestrator:

    @patch("litellm.completion")
    def test_full_flow_symptom(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["symptom"], "reasoning": "pain", "confidence": 0.9}',
            "Tell me more about your headache.",
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="I have a headache", session_id="s1"))
        assert response.agent == AgentType.SYMPTOM
        assert len(response.text) > 0

    @patch("litellm.completion")
    def test_full_flow_medication(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["medication"], "reasoning": "drug", "confidence": 0.9}',
            "Ibuprofen info here.",
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="Tell me about ibuprofen", session_id="s2"))
        assert response.agent == AgentType.MEDICATION

    @patch("litellm.completion")
    def test_fallback_response(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["fallback"], "reasoning": "off topic", "confidence": 0.99}',
            "",
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="Who won the World Cup?", session_id="s3"))
        assert response.agent == AgentType.FALLBACK
        assert response.text == FALLBACK_RESPONSE

    @patch("litellm.completion")
    def test_context_persists_across_turns(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["symptom"], "reasoning": "pain", "confidence": 0.9}',
            "Noted.",
            "Noted refined.",
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Turn 1", session_id="persist"))
        orch.process(UserMessage(text="Turn 2", session_id="persist"))
        ctx = orch._contexts["persist"]
        assert len(ctx.history) == 4  # 2 user + 2 assistant

    @patch("litellm.completion")
    def test_different_sessions_are_isolated(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["lifestyle"], "reasoning": "diet", "confidence": 0.85}',
            "Eat well.",
        )
        orch = Orchestrator()
        orch.process(UserMessage(text="Hello", session_id="userA"))
        orch.process(UserMessage(text="Hello", session_id="userB"))
        assert "userA" in orch._contexts
        assert "userB" in orch._contexts
        assert orch._contexts["userA"] is not orch._contexts["userB"]

    @patch("litellm.completion")
    def test_new_session_created_automatically(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["lifestyle"], "reasoning": "diet", "confidence": 0.8}',
            "Sure!",
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

    @patch("litellm.completion")
    def test_multi_agent_flow(self, mock_llm):
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["symptom", "medication"], "reasoning": "mixed", "confidence": 0.9}',
            "Agent draft.",
            "Merged response.",
        )
        orch = Orchestrator()
        response = orch.process(UserMessage(text="I feel sick after taking ibuprofen", session_id="multi"))
        assert response.agent == AgentType.SYNTHESIZER
        assert response.text == "Merged response."

    @patch("litellm.completion")
    def test_single_agent_synthesized_on_followup(self, mock_llm):
        """Single agent: first turn passes through, second turn gets refined."""
        mock_llm.side_effect = _llm_mock(
            '{"target_agents": ["symptom"], "reasoning": "pain", "confidence": 0.9}',
            "Raw agent reply.",
            "Refined with context.",
        )
        orch = Orchestrator()
        r1 = orch.process(UserMessage(text="I have a headache", session_id="ctx"))
        assert r1.text == "Raw agent reply."  # first turn — no synthesis
        r2 = orch.process(UserMessage(text="It is getting worse", session_id="ctx"))
        assert r2.text == "Refined with context."  # second turn — synthesized
        assert r2.agent == AgentType.SYMPTOM  # still single agent type

    @patch("litellm.completion")
    def test_multi_agent_with_context(self, mock_llm):
        """Multi-agent on a follow-up turn uses synthesizer merge."""
        call_count = {"n": 0}
        def _side_effect(*args, **kwargs):
            call_count["n"] += 1
            messages = kwargs.get("messages") or args[0]
            system = messages[0]["content"].lower() if messages else ""
            if "routing decision" in system or "classify" in system or "router" in system:
                # First call: single agent, subsequent: multi agent
                if call_count["n"] <= 1:
                    content = '{"target_agents": ["symptom"], "reasoning": "pain", "confidence": 0.9}'
                else:
                    content = '{"target_agents": ["symptom", "lifestyle"], "reasoning": "mixed", "confidence": 0.88}'
            elif "quality specialist" in system or "refine" in system:
                content = "Merged follow-up."
            else:
                content = "Agent draft."
            return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])

        mock_llm.side_effect = _side_effect
        orch = Orchestrator()
        r1 = orch.process(UserMessage(text="I have back pain", session_id="mctx"))
        assert r1.agent == AgentType.SYMPTOM
        r2 = orch.process(UserMessage(text="What exercises help with this?", session_id="mctx"))
        assert r2.agent == AgentType.SYNTHESIZER
        assert r2.text == "Merged follow-up."
        ctx = orch._contexts["mctx"]
        assert len(ctx.history) == 4
